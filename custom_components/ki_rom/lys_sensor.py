"""Oversiktssensor per rom – alt kortet trenger ligger i attributtene."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import ATTR_INTEGRASJON, ATTR_TYPE, DOMAIN, LYS_MARKOR
from .entity import LysEntitet
from .jul_entiteter import Nedtelling, Tent


async def sett_opp_lys(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    motor = hass.data[DOMAIN][entry.entry_id].lys
    ut = [Oversikt(motor, rom) for rom in motor.rom]
    if motor.jul.aktiv:
        ut.extend([Nedtelling(motor), Tent(motor)])
    add(ut)


class Oversikt(LysEntitet, SensorEntity):
    platform_domene = "sensor"
    _attr_icon = "mdi:lightbulb-group"

    def __init__(self, motor, rom) -> None:
        super().__init__(motor, rom, "oversikt", "lysscener")

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_track_state_change_event(
            self.hass, self.rom.lys, self._endret))

    @callback
    def _endret(self, _hendelse) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return len([x for x in self.rom.lys
                    if (st := self.hass.states.get(x)) and st.state == "on"])

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "oversikt", **self.motor.oversikt(self.rom)}
