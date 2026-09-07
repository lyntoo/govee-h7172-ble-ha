"""Govee H7172 Ice Maker BLE integration."""

from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.match import ADDRESS, BluetoothCallbackMatcher
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback

from .ble_client import GoveeH7172BLEClient
from .const import DOMAIN
from .models import H7172ConfigEntry, H7172Data

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: H7172ConfigEntry) -> bool:
    """Set up Govee H7172 from a config entry."""
    address: str = entry.unique_id  # type: ignore[assignment]
    assert address is not None

    client = GoveeH7172BLEClient(address)

    @callback
    def _async_ble_callback(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Update state from BLE advertisement passively — no connection needed."""
        client.set_ble_device(service_info.device)
        client.update_from_advertisement(service_info.advertisement)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_ble_callback,
            BluetoothCallbackMatcher({ADDRESS: address}),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    entry.runtime_data = H7172Data(address=address, client=client)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: H7172ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
