"""Sensorer for KI Rom."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    KIND_EFFEKT,
    KIND_META,
    KIND_OVERSIKT,
    KINDS,
    NAVN,
    TOTALT_ID,
    TOTALT_NAVN,
)
from .hub import KiRomHub, signal
from .jul_entiteter import Nedtelling, Tent
from .lys_sensor import Oversikt as LysOversikt


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    hub: KiRomHub = data.hub
    entities: list = []
    for area_id, area_name in hub.areas.items():
        for kind in KINDS:
            entities.append(KiRomSensor(hub, area_id, area_name, kind))
    for kind in KINDS:
        entities.append(KiRomSensor(hub, TOTALT_ID, TOTALT_NAVN, kind))
    entities.extend(lys_sensorer(data))
    async_add_entities(entities)


class KiRomSensor(SensorEntity):
    """Én teller (lys/media/brytere/sensorer/effekt) for ett rom."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hub: KiRomHub, area_id: str, area_name: str, kind: str) -> None:
        self._hub = hub
        self._area_id = area_id
        self._area_name = area_name
        self._kind = kind
        meta = KIND_META[kind]

        self._attr_unique_id = f"{hub.entry.entry_id}_{area_id}_{kind}"
        self._attr_name = meta["navn"]
        self._attr_icon = meta["icon"]
        if kind == KIND_EFFEKT:
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_suggested_display_precision = 0
        if kind == KIND_OVERSIKT:
            self._attr_state_class = None

        device = DeviceInfo(
            identifiers={(DOMAIN, f"{hub.entry.entry_id}_{area_id}")},
            name=area_name,
            manufacturer=NAVN,
            model="Romteller",
        )
        if area_id != TOTALT_ID:
            device["suggested_area"] = area_name
        self._attr_device_info = device

        self._attr_native_value: Any = None
        self._attr_extra_state_attributes: dict[str, Any] = {}
        self._refresh()

    @callback
    def _refresh(self) -> None:
        result = self._hub.compute(self._area_id, self._kind)
        self._attr_native_value = result["value"]
        self._attr_extra_state_attributes = {
            "rom": self._area_name,
            **result["attrs"],
        }

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                signal(self._hub.entry.entry_id, self._area_id),
                self._handle_update,
            )
        )
        self._refresh()

    @callback
    def _handle_update(self) -> None:
        self._refresh()
        self.async_write_ha_state()


def lys_sensorer(data) -> list:
    """Sensorene som fulgte med fra ki_lys: én oversikt per rom, pluss jul."""
    motor = data.lys
    ut: list = [LysOversikt(motor, rom) for rom in motor.rom]
    if motor.jul.aktiv:
        ut.extend([Nedtelling(motor), Tent(motor)])
    return ut
