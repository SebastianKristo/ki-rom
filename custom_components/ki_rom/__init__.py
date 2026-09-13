"""KI Rom – romtellere og lysscener per HA-område.

Slår sammen de tidligere integrasjonene `ki_rom` (tellere og oversikt per rom) og
`ki_lys` (lysscener, soner og julelys). Begge bygde på HA sine områder og hadde hver
sin romliste; nå er det én.

Entitets-ID-ene fra ki_lys er uendret (`button.<rom>_lys_<scene>`,
`switch.<rom>_lys_alle`, `sensor.<rom>_lys_oversikt`), og de beholder attributtet
`integrasjon: ki_lys`, som kortene i ki-cards kjenner scenene på. Ingen dashbord
trenger endring.
"""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, LYS_MARKOR
from .coordinator import LysMotor
from .hub import KiRomHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BUTTON,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
]


class KiRomData:
    """Det plattformene henter ut av hass.data: rommene og lysmotoren."""

    def __init__(self, hub: KiRomHub, lys: LysMotor) -> None:
        self.hub = hub
        self.lys = lys


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _rydd_gamle_lysentiteter(hass)

    hub = KiRomHub(hass, entry)
    await hub.async_start()

    lys = LysMotor(hass, entry)
    lys.les_rom()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = KiRomData(hub, lys)

    if not lys.rom:
        # Ved oppstart kan lysene komme etter oss – prøv igjen når alt er lastet.
        async def _prov_igjen(_hendelse) -> None:
            lys.les_rom()
            if lys.rom:
                await hass.config_entries.async_reload(entry.entry_id)

        entry.async_on_unload(
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _prov_igjen)
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_oppdatert))
    _tjenester(hass)
    return True


async def _oppdatert(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        data: KiRomData = hass.data[DOMAIN].pop(entry.entry_id)
        data.hub.async_stop()
        if not hass.data[DOMAIN]:
            for tj in ("sett", "les_rom", "lagre_naa", "sett_lys",
                       "legg_til_lys", "fjern_lys", "nullstill"):
                hass.services.async_remove(DOMAIN, tj)
    return ok


def _rydd_gamle_lysentiteter(hass: HomeAssistant) -> None:
    """Fjerner rester etter den gamle ki_lys-integrasjonen fra entitetsregisteret.

    Entitets-ID-ene settes eksplisitt av `LysEntitet`, så står en gammel ki_lys-oppføring
    igjen på samme ID, havner den nye på `..._2`. Det skjer hvis ki_lys-mappa ble slettet
    uten at oppsettet ble fjernet først – da blir oppføringene liggende foreldreløse.
    Finnes ki_lys fortsatt som oppsett, rører vi ingenting; fjern oppsettet der først.
    """
    if any(e.domain == LYS_MARKOR for e in hass.config_entries.async_entries()):
        return
    reg = er.async_get(hass)
    doede = [e.entity_id for e in reg.entities.values() if e.platform == LYS_MARKOR]
    for entity_id in doede:
        reg.async_remove(entity_id)
    if doede:
        _LOGGER.info(
            "KI Rom: fjernet %d foreldreløse entiteter fra ki_lys, så scenene beholder "
            "sine gamle entitets-ID-er", len(doede)
        )


def _tjenester(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, "sett"):
        return

    def motorer() -> list[LysMotor]:
        return [d.lys for d in hass.data.get(DOMAIN, {}).values()]

    def finn_rom(m: LysMotor, rom: str | None) -> list[str]:
        if not rom:
            return [r.area_id for r in m.rom]
        return [r.area_id for r in m.rom if rom in (r.area_id, r.navn, r.slug)]

    async def sett(call: ServiceCall) -> None:
        """Setter en scene – i ett rom, eller i alle."""
        scene = call.data["scene"]
        rom = call.data.get("rom")
        for m in motorer():
            if rom:
                for area_id in finn_rom(m, rom):
                    await m.sett(area_id, scene)
            else:
                await m.sett_alle(scene)

    async def les_rom(_call: ServiceCall) -> None:
        """Leser rom og lys på nytt, uten omstart."""
        for m in motorer():
            m.les_rom()

    async def lagre_naa(call: ServiceCall) -> None:
        """Lagrer lysene slik de står nå som overstyring for scenen."""
        for m in motorer():
            for area_id in finn_rom(m, call.data.get("rom")):
                await m.lagre_naa(call.data["scene"], area_id)

    async def sett_lys(call: ServiceCall) -> None:
        for m in motorer():
            await m.sett_lys(
                call.data["scene"], call.data["entity_id"],
                lysstyrke=call.data.get("lysstyrke"),
                paa=call.data.get("pa"),
                kelvin=call.data.get("kelvin"))

    async def legg_til_lys(call: ServiceCall) -> None:
        for m in motorer():
            await m.legg_til_lys(call.data["scene"], call.data["entity_id"])

    async def fjern_lys(call: ServiceCall) -> None:
        for m in motorer():
            await m.fjern_lys(call.data["scene"], call.data["entity_id"])

    async def nullstill(call: ServiceCall) -> None:
        """Fjerner overstyringene for en scene, så rollene gjelder igjen."""
        for m in motorer():
            alle = dict(m.oppsett.get("overstyr") or {})
            alle.pop(call.data["scene"], None)
            m._lagre({"overstyr": alle})

    scene_felt = {vol.Required("scene"): str}
    hass.services.async_register(DOMAIN, "sett", sett, schema=vol.Schema({
        **scene_felt, vol.Optional("rom"): str}))
    hass.services.async_register(DOMAIN, "les_rom", les_rom)
    hass.services.async_register(DOMAIN, "lagre_naa", lagre_naa, schema=vol.Schema({
        **scene_felt, vol.Optional("rom"): str}))
    hass.services.async_register(DOMAIN, "sett_lys", sett_lys, schema=vol.Schema({
        **scene_felt,
        vol.Required("entity_id"): str,
        vol.Optional("lysstyrke"): vol.Coerce(int),
        vol.Optional("pa"): bool,
        vol.Optional("kelvin"): vol.Coerce(int),
    }))
    hass.services.async_register(DOMAIN, "legg_til_lys", legg_til_lys, schema=vol.Schema({
        **scene_felt, vol.Required("entity_id"): str}))
    hass.services.async_register(DOMAIN, "fjern_lys", fjern_lys, schema=vol.Schema({
        **scene_felt, vol.Required("entity_id"): str}))
    hass.services.async_register(DOMAIN, "nullstill", nullstill, schema=vol.Schema(scene_felt))
