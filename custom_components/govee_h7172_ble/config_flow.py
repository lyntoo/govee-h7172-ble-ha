"""Config flow for Govee H7172 BLE integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN, SERVICE_UUID

_LOGGER = logging.getLogger(__name__)


class GoveeH7172ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Govee H7172."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._discovered_devices: dict[str, str] = {}
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle bluetooth discovery."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or discovery_info.address
        }
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Confirm bluetooth discovery."""
        assert self._discovery_info is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or self._discovery_info.address,
                data={CONF_ADDRESS: self._discovery_info.address},
            )

        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or self._discovery_info.address
            },
        )

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Handle user-initiated setup."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS].upper()
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Govee H7172 ({address})",
                data={CONF_ADDRESS: address},
            )

        # Discover nearby devices advertising the Govee service UUID
        discovered = {}
        for info in async_discovered_service_info(self.hass):
            if SERVICE_UUID in info.service_uuids:
                if not self._async_unique_id_in_progress(info.address):
                    discovered[info.address] = f"{info.name} ({info.address})"

        if discovered:
            schema = vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(discovered)}
            )
        else:
            schema = vol.Schema(
                {vol.Required(CONF_ADDRESS): str}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )

    def _async_unique_id_in_progress(self, address: str) -> bool:
        """Check if this address is already being configured."""
        for flow in self._async_in_progress():
            if flow.get("context", {}).get("unique_id") == address:
                return True
        return False
