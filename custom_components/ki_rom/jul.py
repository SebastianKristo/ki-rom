"""Julelys: nedtelling, sesong og gruppene av lys."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    CONF_JUL,
    JUL_GRUPPER,
    STD_JUL_FRA,
    STD_JUL_MAAL,
    STD_JUL_TIL,
)

MND = ["januar", "februar", "mars", "april", "mai", "juni",
       "juli", "august", "september", "oktober", "november", "desember"]


def _dato(mm_dd: str, aar: int) -> date:
    m, _, d = str(mm_dd or "").partition("-")
    return date(aar, int(m or 1), int(d or 1))


def _kort(d: date) -> str:
    return f"{d.day}. {MND[d.month - 1][:3]}"


class JuleMotor:
    """Holder styr på julesesongen: hvilke lys, hvor lenge til, og hvor langt vi er kommet."""

    def __init__(self, hass: HomeAssistant, motor) -> None:
        self.hass = hass
        self.motor = motor

    # ------------------------------------------------------------- oppsett
    @property
    def oppsett(self) -> dict[str, Any]:
        return dict(self.motor.oppsett.get(CONF_JUL) or {})

    @property
    def aktiv(self) -> bool:
        return bool(self.oppsett.get("aktiv"))

    @property
    def lys(self) -> list[str]:
        return list(self.oppsett.get("lys") or [])

    @property
    def fra(self) -> str:
        return str(self.oppsett.get("fra") or STD_JUL_FRA)

    @property
    def til(self) -> str:
        return str(self.oppsett.get("til") or STD_JUL_TIL)

    @property
    def maal(self) -> str:
        return str(self.oppsett.get("maal") or STD_JUL_MAAL)

    # -------------------------------------------------------------- grupper
    def gruppe_for(self, entity_id: str) -> str:
        """Julestjerne, julestake, utelys – eller annet."""
        egne = self.oppsett.get("grupper") or {}
        if entity_id in egne:
            return egne[entity_id]
        st = self.hass.states.get(entity_id)
        navn = f"{entity_id} {(st.attributes.get('friendly_name') if st else '') or ''}".lower()
        for nokkel, _navn, _ikon, monster in JUL_GRUPPER:
            if monster and re.search(monster, navn):
                return nokkel
        return "annet"

    def grupper(self) -> list[dict[str, Any]]:
        ut = []
        for nokkel, navn, ikon, _m in JUL_GRUPPER:
            lys = [x for x in self.lys if self.gruppe_for(x) == nokkel]
            if not lys:
                continue
            ut.append({
                "id": nokkel, "navn": navn, "ikon": ikon,
                "antall": len(lys),
                "lys": [{
                    "entity": x,
                    "navn": self._rom_navn(x),
                    "undertekst": navn[:-1] if navn.endswith("r") else navn,
                    "paa": self._paa(x),
                } for x in lys],
            })
        return ut

    def _rom_navn(self, entity_id: str) -> str:
        """«input_boolean.stue_julestjerne» → «Stue»."""
        st = self.hass.states.get(entity_id)
        raa = (st.attributes.get("friendly_name") if st else None) or entity_id.split(".")[-1]
        raa = re.sub(r"(jule\w+|julelys|lys)", "", str(raa), flags=re.I)
        raa = raa.replace("_", " ").strip(" -·")
        return raa[:1].upper() + raa[1:] if raa else entity_id

    def _paa(self, entity_id: str) -> bool:
        st = self.hass.states.get(entity_id)
        return bool(st and st.state == "on")

    def tent(self) -> int:
        return sum(1 for x in self.lys if self._paa(x))

    # ----------------------------------------------------------- nedtelling
    def nedtelling(self) -> dict[str, Any]:
        """Dager igjen – til julaften i sesongen, ellers til sesongen begynner."""
        i_dag = datetime.now().date()
        aar = i_dag.year
        fra_i_aar = _dato(self.fra, aar)
        til_i_aar = _dato(self.til, aar)
        i_sesong = i_dag >= fra_i_aar or i_dag < til_i_aar

        if i_sesong:
            # sesongen kan ha begynt i fjor, når den går over nyttår
            start = fra_i_aar if i_dag >= fra_i_aar else _dato(self.fra, aar - 1)
            julaften = _dato(self.maal, start.year)
            if i_dag <= julaften:
                fase, maal, overskrift = "jul", julaften, "Julaften"
            else:
                # over julaften: tell ned til sesongen slutter (kan være neste år)
                slutt = til_i_aar if i_dag < til_i_aar else _dato(self.til, aar + 1)
                fase, maal, overskrift = "jul", slutt, "Julesesongen varer til"
                start = julaften
        else:
            fase = "venter"
            start = til_i_aar
            maal = fra_i_aar
            overskrift = "Julesesongen"

        dager = (maal - i_dag).days
        hele = max(1, (maal - start).days)
        gaatt = max(0, min(hele, (i_dag - start).days))
        return {
            "dager": dager,
            "fase": fase,
            "overskrift": overskrift,
            "maal_dato": _kort(maal),
            "prosent": round(gaatt / hele * 100, 1),
            "fra_tekst": _kort(start),
            "til_tekst": _kort(maal),
            "sesong_i_gang": i_sesong,
        }

    # ---------------------------------------------------------------- kjør
    async def alle(self, pa: bool) -> None:
        for x in self.lys:
            domene = x.split(".")[0]
            await self.hass.services.async_call(
                domene, "turn_on" if pa else "turn_off", {"entity_id": x}, blocking=False)

    def oversikt(self) -> dict[str, Any]:
        n = self.nedtelling()
        return {
            **n,
            "lys": self.lys,
            "tent": self.tent(),
            "antall": len(self.lys),
            "grupper": self.grupper(),
            "sesong_fra": self.fra,
            "sesong_til": self.til,
            "maal": self.maal,
        }
