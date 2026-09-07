"""Binary sensor platform for Govee H7172 BLE ice maker."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .models import H7172ConfigEntry, H7172State

BINARY_SENSOR_DESCRIPTIONS = [
    BinarySensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:power",
    ),
    BinarySensorEntityDescription(
        key="alarm",
        translation_key="alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:water-off",
    ),
    BinarySensorEntityDescription(
        key="ice_full",
        translation_key="ice_full",
        icon="mdi:snowflake-alert",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: H7172ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up H7172 binary sensors."""
    entities = [
        GoveeH7172BinarySensor(entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class GoveeH7172BinarySensor(BinarySensorEntity):
    """A binary sensor entity for the Govee H7172."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: H7172ConfigEntry,
        description: BinarySensorEntityDescription,
    ) -> None:
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{entry.unique_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.unique_id)},
            "name": entry.title,
            "manufacturer": "Govee",
            "model": "H7172",
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self._entry.runtime_data.client.register_callback(self._handle_update)
        )

    @callback
    def _handle_update(self, state: H7172State) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool | None:
        state = self._entry.runtime_data.state
        key = self.entity_description.key

        if key == "power":
            return state.power_on
        if key == "alarm":
            return state.alarm_active
        if key == "ice_full":
            return state.ice_full

        return None

    @property
    def available(self) -> bool:
        return self._entry.runtime_data.state.power_on is not None
