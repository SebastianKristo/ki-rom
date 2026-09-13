"""Én knapp per scene per rom."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_INTEGRASJON, ATTR_TYPE, DOMAIN, LYS_MARKOR
from .entity import LysEntitet
from .jul_entiteter import AlleKnapp


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    motor = hass.data[DOMAIN][entry.entry_id].lys
    knapper: list[ButtonEntity] = []
    for rom in motor.rom:
        for scene in motor.scener(rom):
            knapper.append(SceneKnapp(motor, rom, scene))
    if motor.jul.aktiv:
        knapper.extend([AlleKnapp(motor, True), AlleKnapp(motor, False)])
    add(knapper)


class SceneKnapp(LysEntitet, ButtonEntity):
    platform_domene = "button"

    def __init__(self, motor, rom, scene) -> None:
        super().__init__(motor, rom, scene["id"], scene["navn"])
        self.scene = scene
        self._attr_icon = scene.get("ikon")

    @property
    def extra_state_attributes(self) -> dict:
        return {
            ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "scene",
            "scene": self.scene["id"], "rom": self.rom.navn, "area_id": self.rom.area_id,
            "lys": self.rom.lys,
        }

    async def async_press(self) -> None:
        await self.motor.sett(self.rom.area_id, self.scene["id"])
