"""Oppsettsflyt for KI Rom.

Én oppføring dekker både romtellerne og lysscenene. Menyen har «Rom» (hvilke områder
tellerne dekker) øverst; resten er lysoppsettet som fulgte med fra ki_lys.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AREAS,
    CONF_EGNE,
    CONF_EKSKLUDER,
    CONF_EKSKLUDER_ROM,
    CONF_EXCLUDE,
    CONF_INCLUDE_CATEGORY,
    CONF_INCLUDE_GROUPS,
    CONF_EKSTRA_LYS,
    CONF_BRYTERLYS,
    CONF_NATTLYS,
    CONF_OVERGANG,
    CONF_OVERSTYR,
    CONF_ROM,
    CONF_SCENER,
    CONF_SCENER_ROM,
    CONF_SONER,
    CONF_JUL,
    CONF_UTELAT,
    DOMAIN,
    STD_JUL_FRA,
    STD_JUL_MAAL,
    STD_JUL_TIL,
    FOLG_ROLLEN,
    SCENER,
    STD_OVERGANG,
    NAVN,
    STD_SCENER,
    TRACKED_DOMAINS,
)


def _mm_dd(verdi: Any, standard: str) -> str:
    """Godtar «11-01», «1. november» finnes ikke – vi holder oss til MM-DD."""
    tekst = str(verdi or "").strip()
    biter = tekst.split("-")
    if len(biter) == 2 and biter[0].isdigit() and biter[1].isdigit():
        return f"{int(biter[0]):02d}-{int(biter[1]):02d}"
    return standard


def _sone_id(navn: str) -> str:
    navn = (navn or "").lower()
    for fra, til in (("æ", "ae"), ("ø", "o"), ("å", "a"), ("ä", "a"), ("ö", "o"), ("ü", "u")):
        navn = navn.replace(fra, til)
    return "".join(c if c.isalnum() else "_" for c in navn).strip("_") or "sone"


def _felt(entity_id: str) -> str:
    """Entitets-id som feltnavn i skjemaet."""
    return "lys_" + entity_id.replace(".", "__")


def _skjema(d: dict[str, Any]) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_ROM, default=d.get(CONF_ROM, [])): selector.AreaSelector(
            selector.AreaSelectorConfig(multiple=True)),
        vol.Optional(CONF_EKSKLUDER_ROM, default=d.get(CONF_EKSKLUDER_ROM, [])): selector.AreaSelector(
            selector.AreaSelectorConfig(multiple=True)),
        vol.Optional(CONF_EKSKLUDER, default=d.get(CONF_EKSKLUDER, [])): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="light", multiple=True)),
        vol.Optional(CONF_BRYTERLYS, default=d.get(CONF_BRYTERLYS, [])): selector.EntitySelector(
            selector.EntitySelectorConfig(domain=["switch", "input_boolean"], multiple=True)),
        vol.Optional(CONF_NATTLYS, default=d.get(CONF_NATTLYS, [])): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="light", multiple=True)),
        vol.Optional(CONF_SCENER, default=d.get(CONF_SCENER, STD_SCENER)): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[{"value": k, "label": v["navn"]} for k, v in SCENER.items()],
                multiple=True, mode="list")),
        vol.Optional(CONF_OVERGANG, default=d.get(CONF_OVERGANG, STD_OVERGANG)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=15, step=1, unit_of_measurement="s", mode="box")),
    })


ROM_SKJEMA = vol.Schema({
    vol.Optional(CONF_EKSKLUDER_ROM): selector.AreaSelector(
        selector.AreaSelectorConfig(multiple=True)),
    vol.Optional(CONF_AREAS): selector.AreaSelector(
        selector.AreaSelectorConfig(multiple=True)),
    vol.Optional(CONF_EXCLUDE): selector.EntitySelector(
        selector.EntitySelectorConfig(multiple=True, domain=list(TRACKED_DOMAINS))),
    vol.Optional(CONF_INCLUDE_CATEGORY, default=False): selector.BooleanSelector(),
    vol.Optional(CONF_INCLUDE_GROUPS, default=False): selector.BooleanSelector(),
})


class KiRomConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title=NAVN, data={}, options=user_input)
        return self.async_show_form(step_id="user", data_schema=_skjema({}))

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return KiRomOptionsFlow(entry)


class KiRomOptionsFlow(OptionsFlow):
    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._egne: list[dict[str, Any]] = list({**entry.data, **entry.options}.get(CONF_EGNE) or [])
        self._scene: str = "komfort"
        self._rom: str = ""
        self._soner: list[dict[str, Any]] = list({**entry.data, **entry.options}.get(CONF_SONER) or [])

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        return self.async_show_menu(step_id="init",
                                    menu_options=["rom", "innstillinger", "soner", "rom_scener",
                                                  "scener", "overstyr", "julelys"])

    # -------------------------------------------------------------------- rom
    async def async_step_rom(self, user_input: dict[str, Any] | None = None):
        """Hvilke områder romtellerne dekker. Tomt = alle."""
        if user_input is not None:
            return self._flett(user_input)
        d = {**self.entry.data, **self.entry.options}
        return self.async_show_form(
            step_id="rom",
            data_schema=self.add_suggested_values_to_schema(ROM_SKJEMA, d))

    def _flett(self, nytt: dict[str, Any]):
        """Lagrer uten å miste resten av oppsettet."""
        d = {**self.entry.data, **self.entry.options}
        d.update(nytt)
        d[CONF_EGNE] = self._egne
        d.pop("title", None)
        return self.async_create_entry(title="", data=d)

    # ---------------------------------------------------------------- julelys
    async def async_step_julelys(self, user_input: dict[str, Any] | None = None):
        """Julelysene: hvilke lys, når sesongen varer, og hva det telles ned til."""
        d = {**self.entry.data, **self.entry.options}
        jul = dict(d.get(CONF_JUL) or {})
        if user_input is not None:
            ny = {
                "aktiv": bool(user_input.get("aktiv")),
                "lys": list(user_input.get("lys") or []),
                "fra": _mm_dd(user_input.get("fra"), STD_JUL_FRA),
                "til": _mm_dd(user_input.get("til"), STD_JUL_TIL),
                "maal": _mm_dd(user_input.get("maal"), STD_JUL_MAAL),
                "grupper": jul.get("grupper") or {},
            }
            return self.async_create_entry(title="", data={
                **{k: v for k, v in d.items() if k != CONF_JUL},
                CONF_JUL: ny, CONF_EGNE: self._egne,
            })
        return self.async_show_form(step_id="julelys", data_schema=vol.Schema({
            vol.Optional("aktiv", default=jul.get("aktiv", False)): bool,
            vol.Optional("lys", default=jul.get("lys", [])): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["light", "switch", "input_boolean"], multiple=True)),
            vol.Optional("fra", default=jul.get("fra", STD_JUL_FRA)): str,
            vol.Optional("til", default=jul.get("til", STD_JUL_TIL)): str,
            vol.Optional("maal", default=jul.get("maal", STD_JUL_MAAL)): str,
        }))

    # ------------------------------------------------------------------ soner
    async def async_step_soner(self, user_input: dict[str, Any] | None = None):
        """Soner slår flere rom sammen til ett sett scener."""
        if user_input is not None:
            valg = user_input["valg"]
            if valg == "ny":
                return await self.async_step_ny_sone()
            if valg.startswith("slett:"):
                sid = valg.split(":", 1)[1]
                self._soner = [s for s in self._soner if s.get("id") != sid]
                return self._lagre_soner()
        alternativer = [{"value": "ny", "label": "Legg til en sone"}]
        alternativer += [{"value": f"slett:{s['id']}", "label": f"Slett «{s.get('navn') or s['id']}»"}
                         for s in self._soner]
        return self.async_show_form(step_id="soner", data_schema=vol.Schema({
            vol.Required("valg"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=alternativer, mode="list")),
        }))

    async def async_step_ny_sone(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            navn = user_input["navn"]
            sone = {
                "id": _sone_id(navn),
                "navn": navn,
                "rom": list(user_input["rom"]),
                "skjul_enkeltrom": bool(user_input.get("skjul_enkeltrom")),
            }
            self._soner = [s for s in self._soner if s["id"] != sone["id"]] + [sone]
            return self._lagre_soner()
        return self.async_show_form(step_id="ny_sone", data_schema=vol.Schema({
            vol.Required("navn"): str,
            vol.Required("rom"): selector.AreaSelector(selector.AreaSelectorConfig(multiple=True)),
            vol.Optional("skjul_enkeltrom", default=False): bool,
        }))

    def _lagre_soner(self):
        d = {**self.entry.data, **self.entry.options}
        return self.async_create_entry(title="", data={
            **{k: v for k, v in d.items() if k != CONF_SONER},
            CONF_SONER: self._soner, CONF_EGNE: self._egne,
        })

    # ----------------------------------------------------- scener per rom
    async def async_step_rom_scener(self, user_input: dict[str, Any] | None = None):
        """Velg hvilket rom du vil endre utvalget for."""
        if user_input is not None:
            self._rom = user_input["rom"]
            return await self.async_step_rom_valg()
        alternativer = [{"value": r.area_id, "label": r.navn} for r in self._rommene()]
        if not alternativer:
            return self.async_abort(reason="ingen_rom")
        return self.async_show_form(step_id="rom_scener", data_schema=vol.Schema({
            vol.Required("rom"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=alternativer, mode="list")),
        }))

    async def async_step_rom_valg(self, user_input: dict[str, Any] | None = None):
        """Huk av scenene dette rommet skal ha."""
        d = {**self.entry.data, **self.entry.options}
        per_rom = {k: list(v) for k, v in (d.get(CONF_SCENER_ROM) or {}).items()}
        rom = next((r for r in self._rommene() if r.area_id == self._rom), None)

        if user_input is not None:
            valgt = list(user_input.get("scener") or [])
            if user_input.get("som_standard"):
                per_rom.pop(self._rom, None)          # tilbake til standardutvalget
            else:
                per_rom[self._rom] = valgt
            return self.async_create_entry(title="", data={
                **{k: v for k, v in d.items() if k != CONF_SCENER_ROM},
                CONF_SCENER_ROM: per_rom, CONF_EGNE: self._egne,
            })

        naa = per_rom.get(self._rom, d.get(CONF_SCENER) or STD_SCENER)
        alternativer = [{"value": k, "label": v["navn"]} for k, v in SCENER.items()]
        alternativer += [{"value": e["id"], "label": e.get("navn") or e["id"]} for e in self._egne]
        return self.async_show_form(
            step_id="rom_valg",
            data_schema=vol.Schema({
                vol.Optional("scener", default=[x for x in naa]): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=alternativer, multiple=True, mode="list")),
                vol.Optional("som_standard", default=False): bool,
            }),
            description_placeholders={"rom": rom.navn if rom else self._rom})

    # --------------------------------------------------- overstyring per lys
    async def async_step_overstyr(self, user_input: dict[str, Any] | None = None):
        """Velg rommet, og deretter scenen du vil justere.

        Skjemaet listet før hvert lys i hele huset for den valgte scenen. Med tolv rom
        blir det en side med tredve glidebrytere, og det er umulig å finne stua i.
        Nå velges rommet først, og «Alle rom» finnes for den som vil se alt.
        """
        if user_input is not None:
            self._scene = user_input["scene"]
            self._overstyr_rom = user_input.get("rom") or "alle"
            return await self.async_step_lys()
        d = {**self.entry.data, **self.entry.options}
        valgte = d.get(CONF_SCENER) or list(SCENER)
        alternativer = [{"value": k, "label": SCENER[k]["navn"]} for k in SCENER if k in valgte]
        alternativer += [{"value": e["id"], "label": e.get("navn") or e["id"]} for e in self._egne]
        rom_valg = [{"value": "alle", "label": "Alle rom"}]
        rom_valg += [{"value": r.area_id, "label": f"{r.navn} ({len(r.lys)} lys)"}
                     for r in self._rommene() if r.lys]
        return self.async_show_form(step_id="overstyr", data_schema=vol.Schema({
            vol.Required("rom", default=getattr(self, "_overstyr_rom", "alle")):
                selector.SelectSelector(
                    selector.SelectSelectorConfig(options=rom_valg, mode="dropdown")),
            vol.Required("scene"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=alternativer, mode="list")),
        }))

    async def async_step_lys(self, user_input: dict[str, Any] | None = None):
        """Sett lysstyrke per lys, og velg hvilke lys som er med."""
        scene = self._scene
        valgt_rom = getattr(self, "_overstyr_rom", "alle")
        d = {**self.entry.data, **self.entry.options}
        rommene = self._rommene()
        i_rom: list[str] = []
        for rom in rommene:
            i_rom.extend(rom.lys)
        utelat_na = (d.get(CONF_UTELAT) or {}).get(scene) or []
        ekstra_na = (d.get(CONF_EKSTRA_LYS) or {}).get(scene) or []
        overstyr = dict((d.get(CONF_OVERSTYR) or {}).get(scene) or {})

        # Lysene som vises. Har du valgt ett rom, er det bare rommets lys — pluss
        # ekstralys du selv har lagt til der.
        if valgt_rom == "alle":
            alle_lys = sorted(set(i_rom) | set(ekstra_na))
            rom_navn = "alle rom"
        else:
            rom = next((r for r in rommene if r.area_id == valgt_rom), None)
            alle_lys = sorted(rom.lys if rom else [])
            rom_navn = rom.navn if rom else valgt_rom

        if user_input is not None:
            nytt = dict(d.get(CONF_OVERSTYR) or {})
            # Behold overstyringene for lys som ikke er på skjermen nå. Uten dette ville
            # det å redigere stua slettet alt du hadde satt i de andre rommene.
            rad: dict[str, Any] = {k: v for k, v in (nytt.get(scene) or {}).items()
                                   if k not in alle_lys}
            for lys in alle_lys:
                verdi = user_input.get(_felt(lys))
                if verdi is None or int(verdi) == FOLG_ROLLEN:
                    continue
                rad[lys] = {"paa": int(verdi) > 0, "lysstyrke": int(verdi)}
            nytt[scene] = rad
            utelat = {k: list(v) for k, v in (d.get(CONF_UTELAT) or {}).items()}
            ekstra = {k: list(v) for k, v in (d.get(CONF_EKSTRA_LYS) or {}).items()}
            if valgt_rom == "alle":
                utelat[scene] = list(user_input.get("utelat") or [])
                ekstra[scene] = [x for x in (user_input.get("ekstra") or []) if x not in i_rom]
            else:
                # Ett rom av gangen: bare rommets egne lys fjernes fra eller legges til
                # i lista, resten står urørt.
                andre_utelatt = [x for x in utelat_na if x not in alle_lys]
                utelat[scene] = andre_utelatt + list(user_input.get("utelat") or [])
            return self.async_create_entry(title="", data={
                **{k: v for k, v in d.items() if k not in (CONF_OVERSTYR, CONF_UTELAT, CONF_EKSTRA_LYS)},
                CONF_OVERSTYR: nytt, CONF_UTELAT: utelat, CONF_EKSTRA_LYS: ekstra, CONF_EGNE: self._egne,
            })

        felt: dict[Any, Any] = {}
        for lys in alle_lys:
            o = overstyr.get(lys) or {}
            std = o.get("lysstyrke", 0 if o.get("paa") is False else FOLG_ROLLEN)
            felt[vol.Optional(_felt(lys), default=std, description={"suggested_value": std})] = \
                selector.NumberSelector(selector.NumberSelectorConfig(
                    min=FOLG_ROLLEN, max=100, step=1, mode="slider"))
        if valgt_rom == "alle":
            felt[vol.Optional("utelat", default=utelat_na)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True))
            felt[vol.Optional("ekstra", default=ekstra_na)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain="light", multiple=True))
        else:
            # Bare rommets lys kan utelates herfra, og ekstralys utenfra hører ikke til
            # et enkelt rom — de settes under «Alle rom».
            felt[vol.Optional("utelat", default=[x for x in utelat_na if x in alle_lys])] = \
                selector.SelectSelector(selector.SelectSelectorConfig(
                    options=[{"value": x, "label": self._lysnavn(x)} for x in alle_lys],
                    multiple=True, mode="list"))
        return self.async_show_form(
            step_id="lys", data_schema=vol.Schema(felt),
            description_placeholders={
                "scene": SCENER.get(scene, {}).get("navn", scene),
                "rom": rom_navn,
            })

    def _lysmotor(self):
        """Lysmotoren fra hass.data.

        Oppføringen er en `KiRomData` med `.hub` og `.lys` — ikke motoren selv. Stegene
        her plukket den rett ut og kalte `.rom` på den, som ga AttributeError og en tom
        «Feil»-dialog i grensesnittet. Både «Scener per rom» og «Overstyr lys i en
        scene» har vært ødelagt av dette.
        """
        for data in (self.hass.data.get(DOMAIN) or {}).values():
            motor = getattr(data, "lys", data)
            if hasattr(motor, "rom"):
                return motor
        return None

    def _rommene(self) -> list:
        motor = self._lysmotor()
        return list(motor.rom) if motor else []

    def _lysnavn(self, entity_id: str) -> str:
        st = self.hass.states.get(entity_id)
        return (st.attributes.get("friendly_name") if st else None) or entity_id

    async def async_step_innstillinger(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self._flett(user_input)
        d = {**self.entry.data, **self.entry.options}
        return self.async_show_form(step_id="innstillinger", data_schema=_skjema(d))

    # ------------------------------------------------------------ egne scener
    async def async_step_scener(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            valg = user_input["valg"]
            if valg == "ny":
                return await self.async_step_ny()
            if valg.startswith("slett:"):
                navn = valg.split(":", 1)[1]
                self._egne = [e for e in self._egne if e.get("id") != navn]
                return self._lagre()
        alternativer = [{"value": "ny", "label": "Legg til en scene"}]
        alternativer += [{"value": f"slett:{e['id']}", "label": f"Slett «{e.get('navn') or e['id']}»"}
                         for e in self._egne]
        return self.async_show_form(step_id="scener", data_schema=vol.Schema({
            vol.Required("valg"): selector.SelectSelector(
                selector.SelectSelectorConfig(options=alternativer, mode="list")),
        }))

    async def async_step_ny(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            scene = {
                "id": user_input["navn"].lower().replace(" ", "_"),
                "navn": user_input["navn"],
                "ikon": user_input.get("ikon") or "mdi:lightbulb-group",
                "roller": {
                    "tak": [user_input["tak"], user_input["kelvin"]] if user_input["tak"] else None,
                    "lampe": [user_input["lampe"], user_input["kelvin"]] if user_input["lampe"] else None,
                    "stemning": [user_input["stemning"], user_input["kelvin"]] if user_input["stemning"] else None,
                    "arbeid": [user_input["arbeid"], user_input["kelvin"]] if user_input["arbeid"] else None,
                    "nattlys": [user_input["nattlys"], 2200] if user_input["nattlys"] else None,
                },
            }
            if user_input.get("scene"):
                scene["scene"] = user_input["scene"]
            if user_input.get("rom"):
                scene["rom"] = list(user_input["rom"])      # tom = alle rom
            self._egne = [e for e in self._egne if e["id"] != scene["id"]] + [scene]
            return self._lagre()

        prosent = selector.NumberSelector(selector.NumberSelectorConfig(min=0, max=100, step=5, unit_of_measurement="%", mode="slider"))
        return self.async_show_form(step_id="ny", data_schema=vol.Schema({
            vol.Required("navn"): str,
            vol.Optional("ikon", default="mdi:lightbulb-group"): selector.IconSelector(),
            vol.Optional("tak", default=50): prosent,
            vol.Optional("lampe", default=60): prosent,
            vol.Optional("stemning", default=70): prosent,
            vol.Optional("arbeid", default=0): prosent,
            vol.Optional("nattlys", default=0): prosent,
            vol.Optional("kelvin", default=2700): selector.NumberSelector(
                selector.NumberSelectorConfig(min=2000, max=6500, step=100, unit_of_measurement="K", mode="box")),
            vol.Optional("scene"): selector.EntitySelector(selector.EntitySelectorConfig(domain="scene")),
            vol.Optional("rom"): selector.AreaSelector(selector.AreaSelectorConfig(multiple=True)),
        }))

    def _lagre(self):
        d = {**self.entry.data, **self.entry.options}
        d[CONF_EGNE] = self._egne
        return self.async_create_entry(title="", data={k: v for k, v in d.items() if k not in ("title",)})
