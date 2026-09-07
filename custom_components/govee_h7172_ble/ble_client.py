"""BLE client for Govee H7172 ice maker."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.exc import BleakError
from bleak_retry_connector import establish_connection

from .const import (
    WRITE_CHAR_UUID,
    NOTIFY_CHAR_UUID,
    CMD_ALARM,
    CMD_MODE,
    CMD_SWITCH_INFO,
    CMD_WORK_STATUS,
    GOVEE_MANUFACTURER_ID,
    HEADER_APP_TO_DEVICE,
    HEADER_DEVICE_TO_APP,
    PACKET_LEN,
    SWITCH_TYPE_ICE_FULL,
    SWITCH_TYPE_POWER,
)
from .models import H7172State

_LOGGER = logging.getLogger(__name__)


def _make_packet(cmd: int, *payload: int) -> bytes:
    """Build a 20-byte command packet with XOR checksum in last byte."""
    pkt = bytearray(PACKET_LEN)
    pkt[0] = HEADER_APP_TO_DEVICE
    pkt[1] = cmd
    for i, b in enumerate(payload):
        if i + 2 < PACKET_LEN - 1:
            pkt[i + 2] = b & 0xFF
    checksum = 0
    for b in pkt[:-1]:
        checksum ^= b
    pkt[-1] = checksum
    return bytes(pkt)


def _parse_advertisement(adv: AdvertisementData) -> H7172State | None:
    """Parse H7172 state from BLE advertising manufacturer data.

    Format (from com.govee.base2home.pact.BleUtil.parseBleBroadIceMaker):
    Manufacturer data key = 0xEC88 (Govee company ID, little-endian)
    Payload bytes (after company ID stripped by bleak):
      [0..2] = unknown/version
      [3]    = powerOn (0/1)
      [4]    = status byte (bit7 = alarm active)
      [5]    = workStatus (0-5)
      [6..9] = reservation time (int32)
    """
    mfr_data = adv.manufacturer_data
    if not mfr_data:
        return None

    data = mfr_data.get(GOVEE_MANUFACTURER_ID)
    if data is None:
        return None

    if len(data) < 7:
        _LOGGER.debug("H7172 adv: manufacturer data too short (%d bytes)", len(data))
        return None

    # Raw BLE scan record layout (Java parseBleBroadIceMaker):
    #   [i+2] = company ID low byte (0x02)
    #   [i+3] = company ID high byte (0x88)  → bleak key = 0x8802
    #   [i+4] = data[0] = 0xEC (first application byte)
    # So bleak data offsets: powerOn=data[4], statusByte=data[5], workStatus=data[6]
    power_on = bool(data[4] & 0xFF)
    status_byte = data[5] & 0xFF
    work_status = data[6] & 0xFF
    alarm_bit = (status_byte >> 7) & 1

    _LOGGER.debug(
        "H7172 adv: power=%d workStatus=%d alarmBit=%d raw=%s",
        power_on, work_status, alarm_bit, data.hex(),
    )

    return H7172State(
        power_on=power_on,
        work_status=work_status if work_status <= 5 else None,
        alarm_active=bool(alarm_bit),
        from_advertisement=True,
    )


class GoveeH7172BLEClient:
    """BLE client for Govee H7172 ice maker."""

    def __init__(self, address: str) -> None:
        self._address = address
        self._ble_device: BLEDevice | None = None
        self._state = H7172State()
        self._callbacks: list[Callable[[H7172State], None]] = []
        self._connect_lock = asyncio.Lock()
        self._pending_response: asyncio.Future[bytes] | None = None
        self._response_cmd: int | None = None
        self._write_char: BleakGATTCharacteristic | None = None
        self._notify_char: BleakGATTCharacteristic | None = None
        self._client: BleakClient | None = None

    @property
    def state(self) -> H7172State:
        return self._state

    def set_ble_device(self, device: BLEDevice) -> None:
        self._ble_device = device

    def update_from_advertisement(self, adv: AdvertisementData) -> bool:
        """Update state from advertisement data. Returns True if state changed."""
        parsed = _parse_advertisement(adv)
        if parsed is None:
            return False

        changed = False
        if parsed.power_on != self._state.power_on:
            self._state.power_on = parsed.power_on
            changed = True
        if parsed.work_status != self._state.work_status:
            self._state.work_status = parsed.work_status
            changed = True
        # Only update alarm from advertisement when we have no connected state
        if self._state.from_advertisement and parsed.alarm_active != self._state.alarm_active:
            self._state.alarm_active = parsed.alarm_active
            changed = True
        self._state.from_advertisement = True

        if changed:
            self._fire_callbacks()
        return changed

    def register_callback(
        self, callback: Callable[[H7172State], None]
    ) -> Callable[[], None]:
        self._callbacks.append(callback)

        def unregister() -> None:
            self._callbacks.remove(callback)

        return unregister

    def _fire_callbacks(self) -> None:
        for cb in self._callbacks:
            cb(self._state)

    def _on_notification(self, _handle: BleakGATTCharacteristic, data: bytearray) -> None:
        """Handle BLE GATT notification."""
        _LOGGER.warning("H7172 raw notify: len=%d data=%s", len(data), data.hex())
        if len(data) != PACKET_LEN:
            return
        if data[0] != HEADER_DEVICE_TO_APP:
            return

        cmd = data[1]
        payload = data[2:]

        _LOGGER.debug("H7172 notify cmd=0x%02X payload=%s", cmd, payload.hex())

        changed = False

        if cmd == CMD_WORK_STATUS:
            ws = payload[0] & 0xFF
            if ws != self._state.work_status:
                self._state.work_status = ws
                changed = True

        elif cmd == CMD_MODE:
            mode = payload[0] & 0xFF
            if mode != self._state.mode:
                self._state.mode = mode
                changed = True

        elif cmd == CMD_ALARM:
            active = payload[0] == 1
            code = payload[1] & 0xFF
            if active != self._state.alarm_active or code != self._state.alarm_code:
                self._state.alarm_active = active
                self._state.alarm_code = code
                self._state.from_advertisement = False
                changed = True

        elif cmd == CMD_SWITCH_INFO:
            switch_type = payload[0] & 0xFF
            value = payload[1] == 1
            if switch_type == SWITCH_TYPE_POWER:
                if value != self._state.power_on:
                    self._state.power_on = value
                    changed = True
            elif switch_type == SWITCH_TYPE_ICE_FULL:
                if value != self._state.ice_full:
                    self._state.ice_full = value
                    changed = True

        if (
            self._pending_response is not None
            and not self._pending_response.done()
            and self._response_cmd == cmd
        ):
            self._pending_response.set_result(bytes(data))

        if changed:
            self._fire_callbacks()

    async def _write_and_read(self, pkt: bytes, wait_cmd: int) -> bytes | None:
        """Write a command then poll-read the response characteristic."""
        if self._client is None or self._write_char is None or self._notify_char is None:
            return None
        try:
            _LOGGER.warning("H7172 write cmd=0x%02X pkt=%s", wait_cmd, pkt.hex())
            await self._client.write_gatt_char(self._write_char, pkt, response=False)
            # Poll for response (device updates the read char after processing)
            for _ in range(10):
                await asyncio.sleep(0.2)
                resp = await self._client.read_gatt_char(self._notify_char)
                _LOGGER.warning("H7172 read resp: %s", resp.hex())
                if len(resp) == PACKET_LEN and resp[0] == HEADER_DEVICE_TO_APP and resp[1] == wait_cmd:
                    self._on_notification(self._notify_char, bytearray(resp))
                    return bytes(resp)
            _LOGGER.warning("H7172: no response for cmd 0x%02X", wait_cmd)
        except BleakError as e:
            _LOGGER.error("H7172: write/read error: %s", e)
        return None

    def _find_characteristics(
        self, client: BleakClient
    ) -> tuple[BleakGATTCharacteristic | None, BleakGATTCharacteristic | None]:
        """Find write and notify characteristics. Returns (write_char, notify_char)."""
        write_target = WRITE_CHAR_UUID.lower()
        notify_target = NOTIFY_CHAR_UUID.lower()

        write_char = client.services.get_characteristic(write_target)
        notify_char = client.services.get_characteristic(notify_target)

        if write_char is None or notify_char is None:
            _LOGGER.error(
                "H7172: characteristics not found. Services: %s",
                [c.uuid for s in client.services for c in s.characteristics],
            )

        return write_char, notify_char

    async def connect_and_poll(self) -> bool:
        """Connect and poll all states. Returns True on success."""
        if self._ble_device is None:
            _LOGGER.debug("H7172: no BLE device available yet for %s", self._address)
            return False

        async with self._connect_lock:
            client: BleakClient | None = None
            try:
                client = await establish_connection(
                    BleakClient,
                    self._ble_device,
                    self._address,
                    disconnected_callback=lambda _: _LOGGER.debug("H7172: disconnected"),
                )
                self._client = client
                _LOGGER.debug("H7172: connected to %s", self._address)

                self._write_char, self._notify_char = self._find_characteristics(client)
                if self._write_char is None or self._notify_char is None:
                    return False

                # Poll each state: write command, then read response
                for cmd, payload in [
                    (CMD_WORK_STATUS, ()),
                    (CMD_MODE, ()),
                    (CMD_ALARM, ()),
                    (CMD_SWITCH_INFO, (SWITCH_TYPE_ICE_FULL,)),
                ]:
                    await self._write_and_read(_make_packet(cmd, *payload), cmd)
                    await asyncio.sleep(0.3)

                _LOGGER.warning("H7172: poll complete")
                return True

            except BleakError as e:
                _LOGGER.error("H7172: connection error to %s: %s", self._address, e)
                return False
            finally:
                self._write_char = None
                self._notify_char = None
                self._client = None
                if client is not None and client.is_connected:
                    try:
                        await client.disconnect()
                    except BleakError:
                        pass

    async def stop(self) -> None:
        if self._client and self._client.is_connected:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
        self._client = None
        self._write_char = None
        self._notify_char = None
