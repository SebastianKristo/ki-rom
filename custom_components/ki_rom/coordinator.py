"""Motoren: finner lysene i hvert rom, gir dem en rolle, og setter scenene."""
from __future__ import annotations

import logging
import re
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar, device_registry as dr, entity_registry as er

from .const import (
    CONF_EGNE,
    CONF_EKSKLUDER,
    CONF_EKSTRA_LYS,
    CONF_BRYTERLYS,
    CONF_NATTLYS,
    CONF_OVERGANG,
    CONF_OVERSTYR,
    CONF_ROM,
    CONF_SCENER,
    CONF_SCENER_ROM,
    CONF_SONER,
    CONF_UTELAT,
    CONF_AREAS,
    CONF_EKSKLUDER_ROM,
    CONF_EXCLUDE,
    DOMAIN,
    FOLG_ROLLEN,
    OPPSKRIFT,
    ROLLER,
    SCENER,
    STD_OVERGANG,
    STD_ROLLE,
    STD_SCENER,
)

from .jul import JuleMotor

_LOGGER = logging.getLogger(__name__)


class Rom:
    """Ett rom – eller en sone som slår flere rom sammen."""

    def __init__(self, area_id: str, navn: str, omrader: list[str] | None = None) -> None:
        self.area_id = area_id                       # id-en scenene knyttes til
        self.navn = navn
        self.omrader = omrader or [area_id]          # områdene sonen dekker
        self.lys: list[str] = []

    @property
    def er_sone(self) -> bool:
        return len(self.omrader) > 1

    @property
    def slug(self) -> str:
        navn = (self.navn or self.area_id).lower()
        for fra, til in (("æ", "ae"), ("ø", "o"), ("å", "a"), ("ä", "a"), ("ö", "o"), ("ü", "u")):
            navn = navn.replace(fra, til)
        return re.sub(r"[^a-z0-9_]+", "_", navn).strip("_") or self.area_id


def _slug(navn: str) -> str:
    navn = (navn or "").lower()
    for fra, til in (("æ", "ae"), ("ø", "o"), ("å", "a"), ("ä", "a"), ("ö", "o"), ("ü", "u")):
        navn = navn.replace(fra, til)
    return re.sub(r"[^a-z0-9_]+", "_", navn).strip("_") or "sone"


class LysMotor:
    """Leser rom og lys fra Home Assistant, og kjører scenene."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.rom: list[Rom] = []
        self.jul = JuleMotor(hass, self)
        self._lyttere: list = []

    # ------------------------------------------------------------- oppsett
    @property
    def oppsett(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    @property
    def overgang(self) -> int:
        return int(self.oppsett.get(CONF_OVERGANG) or STD_OVERGANG)

    @property
    def valgte_scener(self) -> list[str]:
        valgt = self.oppsett.get(CONF_SCENER) or STD_SCENER
        return [s for s in STD_SCENER if s in valgt]

    def scener_for(self, rom: Rom) -> list[str]:
        """Hvert rom kan ha sitt eget utvalg. Uten eget valg gjelder standarden."""
        eget = (self.oppsett.get(CONF_SCENER_ROM) or {}).get(rom.area_id)
        if eget is None:
            return self.valgte_scener
        return [s for s in STD_SCENER if s in eget]

    @property
    def egne(self) -> list[dict[str, Any]]:
        return list(self.oppsett.get(CONF_EGNE) or [])

    def _omraade_for(self, entity_id: str) -> str | None:
        """Hvilket område et lys hører til: entitetens eget, ellers enhetens.
        De fleste lys arver området fra enheten – derfor holder det ikke å
        spørre om entiteter med område satt direkte."""
        reg = er.async_get(self.hass)
        oppf = reg.async_get(entity_id)
        if oppf is None:
            return None
        if oppf.area_id:
            return oppf.area_id
        if oppf.device_id:
            enhet = dr.async_get(self.hass).async_get(oppf.device_id)
            if enhet:
                return enhet.area_id
        return None

    def les_rom(self) -> None:
        """Finner lysene i hvert valgte rom, minus de ekskluderte."""
        områder = ar.async_get(self.hass)
        ekskl = set(self.oppsett.get(CONF_EKSKLUDER) or [])
        ekskl |= set(self.oppsett.get(CONF_EXCLUDE) or [])
        valgte = list(self.oppsett.get(CONF_ROM) or [])
        if not valgte:
            # Ikke satt opp egne lysrom? Bruk romlista fra KI Rom. Er heller ikke den
            # satt, dekker KI Rom alle områder – og da gjør lysscenene det samme.
            valgte = list(self.oppsett.get(CONF_AREAS) or [])
        if not valgte:
            valgte = [a.id for a in ar.async_get(self.hass).async_list_areas()]
        hopp_over = set(self.oppsett.get(CONF_EKSKLUDER_ROM) or [])
        valgte = [a for a in valgte if a not in hopp_over]
        self.rom = []
        if not valgte:
            return

        # ett oppslag over alle lys, så slipper vi å spørre registeret per rom
        per_omraade: dict[str, list[str]] = {}
        uten_omraade: list[str] = []

        def _legg_til(entity_id: str) -> None:
            if entity_id in ekskl:
                return
            omr = self._omraade_for(entity_id)
            if omr:
                per_omraade.setdefault(omr, []).append(entity_id)
            else:
                uten_omraade.append(entity_id)

        for st in self.hass.states.async_all("light"):
            _legg_til(st.entity_id)

        # Lys som henger på en bryter eller et relé er `switch`-entiteter, og ble aldri
        # funnet her. De må listes i oppsettet, for vi kan ikke gjette hvilke brytere
        # som er lys og hvilke som er varmekabler.
        for entity_id in (self.oppsett.get(CONF_BRYTERLYS) or []):
            if self.hass.states.get(entity_id):
                _legg_til(entity_id)
            else:
                _LOGGER.warning("KI Lys: «%s» finnes ikke, og kan ikke styres.", entity_id)

        if uten_omraade:
            _LOGGER.warning(
                "KI Lys: disse lysene har ingen område i Home Assistant og blir derfor "
                "ikke styrt — heller ikke slått av i nattmodus: %s",
                ", ".join(sorted(uten_omraade)))

        # sonene først, så vi vet hvilke enkeltrom som eventuelt skal skjules
        soner = self.oppsett.get(CONF_SONER) or []
        skjult: set[str] = set()
        for sone in soner:
            omrader = [a for a in (sone.get("rom") or []) if a in valgte or not valgte]
            if not omrader:
                continue
            lys: list[str] = []
            for a in omrader:
                lys.extend(per_omraade.get(a, []))
            rom = Rom(sone.get("id") or _slug(sone.get("navn", "sone")),
                      sone.get("navn") or "Sone", omrader)
            rom.lys = sorted(set(lys))
            if sone.get("skjul_enkeltrom"):
                skjult.update(omrader)
            if rom.lys:
                self.rom.append(rom)

        for area_id in valgte:
            if area_id in skjult:
                continue
            omr = områder.async_get_area(area_id)
            rom = Rom(area_id, omr.name if omr else area_id)
            rom.lys = sorted(per_omraade.get(area_id, []))
            if rom.lys:
                self.rom.append(rom)
            else:
                _LOGGER.warning(
                    "KI Lys: fant ingen lys i «%s». Ligger lysene i dette området, "
                    "og er de ikke valgt bort i oppsettet?", rom.navn)

    # --------------------------------------------------------------- roller
    def rolle(self, entity_id: str) -> str:
        """Hvilken rolle lyset spiller: tak, lampe, stemning, arbeid eller nattlys."""
        if entity_id in (self.oppsett.get(CONF_NATTLYS) or []):
            return "nattlys"
        st = self.hass.states.get(entity_id)
        navn = f"{entity_id} {(st.attributes.get('friendly_name') if st else '') or ''}".lower()
        for rolle, mønster in ROLLER:
            if re.search(mønster, navn):
                return rolle
        return STD_ROLLE

    def roller_i(self, rom: Rom) -> dict[str, list[str]]:
        ut: dict[str, list[str]] = {}
        for lys in rom.lys:
            ut.setdefault(self.rolle(lys), []).append(lys)
        return ut

    # ------------------------------------------------------------ overstyring
    def overstyringer(self, scene: str) -> dict[str, dict]:
        return dict((self.oppsett.get(CONF_OVERSTYR) or {}).get(scene) or {})

    def lys_i_scene(self, rom: Rom, scene: str) -> list[str]:
        """Lysene scenen gjelder for: rommets lys, minus utelatte, pluss ekstra."""
        utelat = set((self.oppsett.get(CONF_UTELAT) or {}).get(scene) or [])
        ekstra = [x for x in ((self.oppsett.get(CONF_EKSTRA_LYS) or {}).get(scene) or [])
                  if self._hoer_til(x, rom)]
        return [x for x in rom.lys if x not in utelat] + [x for x in ekstra if x not in rom.lys]

    def _hoer_til(self, entity_id: str, rom: Rom) -> bool:
        """Ekstra lys kan være skrevet som «light.x» eller «rom:light.x»."""
        if ":" not in entity_id:
            return True
        omr, _, _ = entity_id.partition(":")
        return omr in (rom.area_id, rom.slug, rom.navn)

    def _innstilling(self, lys: str, scene: str, oppskrift: dict) -> tuple[int, int] | None:
        """Overstyring for dette lyset i denne scenen, ellers rollens verdi."""
        o = self.overstyringer(scene).get(lys)
        fra_rolle = oppskrift.get(self.rolle(lys))
        if not o:
            return fra_rolle
        if o.get("paa") is False:
            return None
        styrke = o.get("lysstyrke", FOLG_ROLLEN)
        kelvin = o.get("kelvin") or (fra_rolle[1] if fra_rolle else 2700)
        if styrke is None or int(styrke) == FOLG_ROLLEN:
            if fra_rolle is None:
                return (60, kelvin) if o.get("paa") else None
            return (fra_rolle[0], kelvin)
        if int(styrke) <= 0:
            return None
        return (int(styrke), kelvin)

    # ---------------------------------------------------------------- kjør
    async def sett(self, area_id: str, scene: str) -> None:
        """Setter en scene i ett rom."""
        rom = next((r for r in self.rom if r.area_id == area_id), None)
        if rom is None:
            return

        egen = next((e for e in self.egne if e.get("id") == scene), None)
        if egen:
            await self._kjor_egen(rom, egen)
            return

        oppskrift = OPPSKRIFT.get(scene)
        if oppskrift is None:
            return
        for lys in self.lys_i_scene(rom, scene):
            await self._sett_lys(lys, self._innstilling(lys, scene, oppskrift))

    async def _kjor_egen(self, rom: Rom, egen: dict[str, Any]) -> None:
        """Egen scene: enten faste verdier per rolle, eller en scene/skript."""
        if egen.get("scene"):
            await self.hass.services.async_call("scene", "turn_on", {"entity_id": egen["scene"]}, blocking=False)
            return
        if egen.get("skript"):
            domene, tjeneste = str(egen["skript"]).split(".", 1)
            await self.hass.services.async_call(domene, tjeneste, {}, blocking=False)
            return
        oppskrift = {r: (tuple(v) if v else None) for r, v in (egen.get("roller") or {}).items()}
        for lys in self.lys_i_scene(rom, egen.get("id", "")):
            await self._sett_lys(lys, self._innstilling(lys, egen.get("id", ""), oppskrift))

    def _stotter_overgang(self, entity_id: str) -> bool:
        """Bare lys som melder TRANSITION (bit 32) tåler «transition» i kallet.

        Sender vi det til et lys som ikke støtter det, avviser Home Assistant hele
        tjenestekallet — og da blir lyset stående på. Det rammer typisk én enkelt lampe
        i et ellers fungerende oppsett, som er vondt å feilsøke: alle de andre slukker.
        """
        st = self.hass.states.get(entity_id)
        if not st:
            return False
        try:
            return bool(int(st.attributes.get("supported_features") or 0) & 32)
        except (TypeError, ValueError):
            return False

    async def _sett_lys(self, entity_id: str, innstilling: tuple[int, int] | None) -> None:
        domene = entity_id.split(".")[0]
        if innstilling is None:
            # switch, input_boolean og lignende har ikke «transition», og skal kalles
            # i sitt eget domene — ikke i light.
            data: dict[str, Any] = {"entity_id": entity_id}
            if domene == "light" and self.overgang and self._stotter_overgang(entity_id):
                data["transition"] = self.overgang
            await self.hass.services.async_call(domene, "turn_off", data, blocking=False)
            return
        if domene != "light":
            # Et lys på en bryter kan bare av og på — lysstyrke og farge finnes ikke
            await self.hass.services.async_call(domene, "turn_on", {"entity_id": entity_id}, blocking=False)
            return
        prosent, kelvin = innstilling
        data: dict[str, Any] = {
            "entity_id": entity_id,
            "brightness_pct": max(1, min(100, int(prosent))),
        }
        if self.overgang and self._stotter_overgang(entity_id):
            data["transition"] = self.overgang
        st = self.hass.states.get(entity_id)
        moduser = (st.attributes.get("supported_color_modes") or []) if st else []
        if "color_temp" in moduser:
            data["color_temp_kelvin"] = int(kelvin)
        await self.hass.services.async_call("light", "turn_on", data, blocking=False)

    def fang(self, rom: Rom, scene: str) -> dict[str, dict]:
        """Leser lysene slik de står nå, som overstyringer for scenen."""
        ut: dict[str, dict] = {}
        for lys in self.lys_i_scene(rom, scene):
            st = self.hass.states.get(lys)
            if st is None:
                continue
            if st.state != "on":
                ut[lys] = {"paa": False}
                continue
            lysstyrke = st.attributes.get("brightness")
            rad: dict[str, Any] = {"paa": True}
            if lysstyrke is not None:
                rad["lysstyrke"] = max(1, round(int(lysstyrke) / 255 * 100))
            kelvin = st.attributes.get("color_temp_kelvin")
            if kelvin:
                rad["kelvin"] = int(kelvin)
            ut[lys] = rad
        return ut

    async def lagre_naa(self, scene: str, area_id: str | None = None) -> None:
        """Lagrer dagens lysbilde som overstyring, i ett rom eller i alle."""
        alle = dict(self.oppsett.get(CONF_OVERSTYR) or {})
        for r in self.rom:
            if area_id and r.area_id != area_id:
                continue
            alle.setdefault(scene, {}).update(self.fang(r, scene))
        self._lagre({CONF_OVERSTYR: alle})

    async def sett_lys(self, scene: str, entity_id: str, lysstyrke: int | None = None,
                       paa: bool | None = None, kelvin: int | None = None) -> None:
        """Setter én overstyring – eller fjerner den når alt er tomt."""
        alle = dict(self.oppsett.get(CONF_OVERSTYR) or {})
        rad = dict((alle.get(scene) or {}).get(entity_id) or {})
        if lysstyrke is not None:
            rad["lysstyrke"] = int(lysstyrke)
        if paa is not None:
            rad["paa"] = bool(paa)
        if kelvin is not None:
            rad["kelvin"] = int(kelvin)
        scenen = dict(alle.get(scene) or {})
        if rad:
            scenen[entity_id] = rad
        else:
            scenen.pop(entity_id, None)
        alle[scene] = scenen
        self._lagre({CONF_OVERSTYR: alle})

    async def legg_til_lys(self, scene: str, entity_id: str) -> None:
        """Tar et lys inn i scenen igjen, eller legger til et utenfra."""
        utelat = {k: list(v) for k, v in (self.oppsett.get(CONF_UTELAT) or {}).items()}
        ekstra = {k: list(v) for k, v in (self.oppsett.get(CONF_EKSTRA_LYS) or {}).items()}
        utelat[scene] = [x for x in utelat.get(scene, []) if x != entity_id]
        i_rom = any(entity_id in r.lys for r in self.rom)
        if not i_rom and entity_id not in ekstra.get(scene, []):
            ekstra.setdefault(scene, []).append(entity_id)
        self._lagre({CONF_UTELAT: utelat, CONF_EKSTRA_LYS: ekstra})

    async def fjern_lys(self, scene: str, entity_id: str) -> None:
        """Tar et lys ut av scenen."""
        utelat = {k: list(v) for k, v in (self.oppsett.get(CONF_UTELAT) or {}).items()}
        ekstra = {k: list(v) for k, v in (self.oppsett.get(CONF_EKSTRA_LYS) or {}).items()}
        ekstra[scene] = [x for x in ekstra.get(scene, []) if x != entity_id]
        if entity_id not in utelat.get(scene, []):
            utelat.setdefault(scene, []).append(entity_id)
        self._lagre({CONF_UTELAT: utelat, CONF_EKSTRA_LYS: ekstra})

    def _lagre(self, nytt: dict[str, Any]) -> None:
        """Skriver til options uten å laste integrasjonen på nytt."""
        options = {**self.entry.options, **nytt}
        self.hass.config_entries.async_update_entry(self.entry, options=options)

    async def sett_alle(self, scene: str) -> None:
        for rom in self.rom:
            await self.sett(rom.area_id, scene)

    # -------------------------------------------------------------- oversikt
    def scener(self, rom: Rom | None = None) -> list[dict[str, Any]]:
        valgte = self.scener_for(rom) if rom else self.valgte_scener
        ut = [{"id": s, **SCENER[s]} for s in valgte]
        for e in self.egne:
            rom_valg = e.get("rom")           # egen scene kan gjelde bare noen rom
            if rom and rom_valg and rom.area_id not in rom_valg:
                continue
            ut.append({"id": e.get("id"), "navn": e.get("navn") or e.get("id"),
                       "ikon": e.get("ikon") or "mdi:lightbulb-group", "rekkefolge": 90})
        return sorted(ut, key=lambda x: x.get("rekkefolge", 50))

    def oversikt(self, rom: Rom) -> dict[str, Any]:
        roller = self.roller_i(rom)
        return {
            "rom": rom.navn, "area_id": rom.area_id, "area_ids": rom.omrader,
            "er_sone": rom.er_sone, "slug": rom.slug,
            "lys": rom.lys, "roller": roller,
            "scener": [{**s, "entity": f"button.{rom.slug}_lys_{s['id']}"} for s in self.scener(rom)],
            "antall_lys": len(rom.lys),
            "paa_naa": [x for x in rom.lys if (self.hass.states.get(x) or None) and self.hass.states.get(x).state == "on"],
        }
