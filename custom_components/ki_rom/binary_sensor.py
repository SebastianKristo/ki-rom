"""Binærsensor: går julesesongen nå?"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN  # noqa: F401
from .jul_entiteter import ISesong


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    motor = hass.data[DOMAIN][entry.entry_id].lys
    if motor.jul.aktiv:
        add([ISesong(motor)])
