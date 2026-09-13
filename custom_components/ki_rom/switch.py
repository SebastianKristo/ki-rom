"""Bryter per rom: på setter Komfort, av slår alt av."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_INTEGRASJON, ATTR_TYPE, DOMAIN, LYS_MARKOR
from .entity import LysEntitet
from .jul_entiteter import Sesong


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    motor = hass.data[DOMAIN][entry.entry_id].lys
    ut = [RomLys(motor, rom) for rom in motor.rom]
    if motor.jul.aktiv:
        ut.append(Sesong(motor))
    add(ut)


class RomLys(LysEntitet, SwitchEntity):
    platform_domene = "switch"
    _attr_icon = "mdi:lightbulb-group"

    def __init__(self, motor, rom) -> None:
        super().__init__(motor, rom, "alle", "lys")

    @property
    def is_on(self) -> bool:
        return any((st := self.hass.states.get(x)) and st.state == "on" for x in self.rom.lys)

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "rom", "rom": self.rom.navn, "area_id": self.rom.area_id}

    async def async_turn_on(self, **_kwargs) -> None:
        await self.motor.sett(self.rom.area_id, "komfort")

    async def async_turn_off(self, **_kwargs) -> None:
        await self.motor.sett(self.rom.area_id, "av")
