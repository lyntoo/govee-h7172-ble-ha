"""Data models for Govee H7172 BLE integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from .ble_client import GoveeH7172BLEClient


@dataclass
class H7172State:
    """State of the Govee H7172 ice maker."""

    power_on: bool | None = None          # True = on, False = off
    work_status: int | None = None        # 0-5 (see WORK_STATUS in const.py)
    mode: int | None = None               # 1=large, 2=medium, 3=small
    alarm_active: bool | None = None      # True = alarm (lack water) active
    alarm_code: int | None = None         # raw alarm code from device
    ice_full: bool | None = None          # True = ice tray full
    from_advertisement: bool = False      # True = updated from BLE adv (no connection)

    @property
    def work_status_str(self) -> str | None:
        """Return human-readable work status."""
        from .const import WORK_STATUS
        if self.work_status is None:
            return None
        return WORK_STATUS.get(self.work_status, f"unknown_{self.work_status}")

    @property
    def mode_str(self) -> str | None:
        """Return human-readable mode."""
        from .const import MODE
        if self.mode is None:
            return None
        return MODE.get(self.mode, f"unknown_{self.mode}")


type H7172ConfigEntry = ConfigEntry["H7172Data"]


@dataclass
class H7172Data:
    """Runtime data for H7172 config entry."""

    address: str
    client: "GoveeH7172BLEClient"
    state: H7172State = field(default_factory=H7172State)
