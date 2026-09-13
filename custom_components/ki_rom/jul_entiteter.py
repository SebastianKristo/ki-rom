"""Entitetene for julelysene – nedtelling, sesong, antall tent og knapper."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change

from .const import ATTR_INTEGRASJON, ATTR_TYPE, DOMAIN, LYS_MARKOR


class JulEntitet(Entity):
    _attr_should_poll = False
    platform_domene = "sensor"

    def __init__(self, motor, nokkel: str, navn: str) -> None:
        self.motor = motor
        self.jul = motor.jul
        self._attr_unique_id = f"{motor.entry.entry_id}_jul_{nokkel}"
        self._attr_name = navn
        self.entity_id = f"{self.platform_domene}.ki_jul_{nokkel}"

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.motor.entry.entry_id}_jul")},
            name="Julelys", manufacturer="KI", model="Julelys")

    async def async_added_to_hass(self) -> None:
        if self.jul.lys:
            self.async_on_remove(async_track_state_change_event(
                self.hass, self.jul.lys, self._endret))
        # nedtellingen skifter ved midnatt
        self.async_on_remove(async_track_time_change(
            self.hass, self._endret, hour=0, minute=0, second=5))

    @callback
    def _endret(self, _hendelse=None) -> None:
        self.async_write_ha_state()


class Nedtelling(JulEntitet, SensorEntity):
    _attr_icon = "mdi:calendar-star"
    _attr_native_unit_of_measurement = "dager"

    def __init__(self, motor) -> None:
        super().__init__(motor, "nedtelling", "Jul nedtelling")

    @property
    def native_value(self) -> int:
        return self.jul.nedtelling()["dager"]

    @property
    def icon(self) -> str:
        return "mdi:pine-tree" if self.jul.nedtelling()["fase"] == "jul" else "mdi:calendar-star"

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "jul", **self.jul.oversikt()}


class Tent(JulEntitet, SensorEntity):
    _attr_icon = "mdi:string-lights"
    platform_domene = "sensor"

    def __init__(self, motor) -> None:
        super().__init__(motor, "tent", "Julelys tent")

    @property
    def native_value(self) -> int:
        return self.jul.tent()

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "jul_tent",
                "av_totalt": len(self.jul.lys), "lys": self.jul.lys}


class Sesong(JulEntitet, SwitchEntity):
    """På tenner julelysene, av slukker dem."""

    platform_domene = "switch"
    _attr_icon = "mdi:pine-tree"

    def __init__(self, motor) -> None:
        super().__init__(motor, "sesong", "Julesesong")

    @property
    def is_on(self) -> bool:
        return self.jul.tent() > 0

    @property
    def extra_state_attributes(self) -> dict:
        n = self.jul.nedtelling()
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "jul_sesong",
                "sesong_i_gang": n["sesong_i_gang"], "tent": self.jul.tent()}

    async def async_turn_on(self, **_kwargs) -> None:
        await self.jul.alle(True)

    async def async_turn_off(self, **_kwargs) -> None:
        await self.jul.alle(False)


class ISesong(JulEntitet, BinarySensorEntity):
    """Er vi inne i julesesongen akkurat nå?"""

    platform_domene = "binary_sensor"
    _attr_icon = "mdi:calendar-check"

    def __init__(self, motor) -> None:
        super().__init__(motor, "i_sesong", "Julesesong pågår")

    @property
    def is_on(self) -> bool:
        return bool(self.jul.nedtelling()["sesong_i_gang"])

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "jul_i_sesong",
                "fra": self.jul.fra, "til": self.jul.til}


class AlleKnapp(JulEntitet, ButtonEntity):
    platform_domene = "button"

    def __init__(self, motor, pa: bool) -> None:
        super().__init__(motor, "alle_pa" if pa else "alle_av",
                         "Alle julelys på" if pa else "Alle julelys av")
        self.pa = pa
        self._attr_icon = "mdi:lightbulb-on-outline" if pa else "mdi:lightbulb-off-outline"

    @property
    def extra_state_attributes(self) -> dict:
        return {ATTR_INTEGRASJON: LYS_MARKOR, ATTR_TYPE: "jul_knapp", "pa": self.pa}

    async def async_press(self) -> None:
        await self.jul.alle(self.pa)
