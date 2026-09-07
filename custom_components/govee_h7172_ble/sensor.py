"""Sensor platform for Govee H7172 BLE ice maker."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, WORK_STATUS, MODE
from .models import H7172ConfigEntry, H7172State

SENSOR_DESCRIPTIONS = [
    SensorEntityDescription(
        key="work_status",
        translation_key="work_status",
        icon="mdi:snowflake",
    ),
    SensorEntityDescription(
        key="mode",
        translation_key="mode",
        icon="mdi:cube-outline",
    ),
    SensorEntityDescription(
        key="alarm_code",
        translation_key="alarm_code",
        icon="mdi:alert",
        entity_registry_enabled_default=False,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: H7172ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up H7172 sensors."""
    data = entry.runtime_data
    entities = [
        GoveeH7172Sensor(entry, description) for description in SENSOR_DESCRIPTIONS
    ]
    async_add_entities(entities)


class GoveeH7172Sensor(SensorEntity):
    """A sensor entity for the Govee H7172."""

    _attr_has_entity_name = True

    def __init__(
        self,
        entry: H7172ConfigEntry,
        description: SensorEntityDescription,
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
        """Register callback when added."""
        self.async_on_remove(
            self._entry.runtime_data.client.register_callback(self._handle_update)
        )

    @callback
    def _handle_update(self, state: H7172State) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> str | int | None:
        state = self._entry.runtime_data.state
        key = self.entity_description.key

        if key == "work_status":
            if state.work_status is None:
                return None
            return WORK_STATUS.get(state.work_status, f"unknown_{state.work_status}")

        if key == "mode":
            if state.mode is None:
                return None
            return MODE.get(state.mode, f"unknown_{state.mode}")

        if key == "alarm_code":
            return state.alarm_code

        return None

    @property
    def available(self) -> bool:
        return self._entry.runtime_data.state.power_on is not None
