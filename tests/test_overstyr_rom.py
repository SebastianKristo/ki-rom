"""Finjustering av scener per rom: bare det valgte rommet skal endres."""
from types import SimpleNamespace

from custom_components.ki_rom.config_flow import KiRomOptionsFlow
from custom_components.ki_rom.const import (
    CONF_EKSTRA_LYS, CONF_OVERSTYR, CONF_UTELAT, FOLG_ROLLEN,
)


def _felt(e):
    from custom_components.ki_rom.config_flow import _felt as f
    return f(e)


def _flyt(overstyr, utelat=None, rom_valgt="stue"):
    f = object.__new__(KiRomOptionsFlow)
    stue = SimpleNamespace(area_id="stue", navn="Stue",
                           lys=["light.stue_tak", "light.stue_gulv"])
    kjokken = SimpleNamespace(area_id="kjokken", navn="Kjøkken",
                              lys=["light.kjokken_benk"])
    f.hass = SimpleNamespace(
        data={"ki_rom": {"1": SimpleNamespace(rom=[stue, kjokken])}},
        states=SimpleNamespace(get=lambda e: None))
    f.entry = SimpleNamespace(
        data={}, options={CONF_OVERSTYR: overstyr, CONF_UTELAT: utelat or {},
                          CONF_EKSTRA_LYS: {}})
    f._scene = "kveld"
    f._overstyr_rom = rom_valgt
    f._egne = []
    f.lagret = {}
    f.async_create_entry = lambda title, data: setattr(f, "lagret", data) or data
    return f


def test_redigering_av_ett_rom_rorer_ikke_de_andre():
    """Dette er hele poenget: lagrer du stua, skal kjøkkenet stå urørt.

    Før skrev steget hele scenen på nytt fra feltene på skjermen, så alt du hadde satt
    i andre rom ble slettet i det du lagret ett av dem."""
    import asyncio
    start = {"kveld": {
        "light.stue_tak": {"paa": True, "lysstyrke": 40},
        "light.kjokken_benk": {"paa": True, "lysstyrke": 70},
    }}
    f = _flyt(start, rom_valgt="stue")
    svar = {_felt("light.stue_tak"): 25, _felt("light.stue_gulv"): 60, "utelat": []}
    data = asyncio.get_event_loop().run_until_complete(f.async_step_lys(svar))
    rad = data[CONF_OVERSTYR]["kveld"]
    assert rad["light.stue_tak"]["lysstyrke"] == 25
    assert rad["light.stue_gulv"]["lysstyrke"] == 60
    assert rad["light.kjokken_benk"]["lysstyrke"] == 70, "kjøkkenet ble overskrevet"


def test_folg_rollen_fjerner_overstyringen():
    import asyncio
    f = _flyt({"kveld": {"light.stue_tak": {"paa": True, "lysstyrke": 40}}})
    svar = {_felt("light.stue_tak"): FOLG_ROLLEN, _felt("light.stue_gulv"): FOLG_ROLLEN,
            "utelat": []}
    data = asyncio.get_event_loop().run_until_complete(f.async_step_lys(svar))
    assert "light.stue_tak" not in data[CONF_OVERSTYR]["kveld"]


def test_null_slar_lyset_av_i_scenen():
    import asyncio
    f = _flyt({})
    svar = {_felt("light.stue_tak"): 0, _felt("light.stue_gulv"): FOLG_ROLLEN, "utelat": []}
    data = asyncio.get_event_loop().run_until_complete(f.async_step_lys(svar))
    o = data[CONF_OVERSTYR]["kveld"]["light.stue_tak"]
    assert o["paa"] is False and o["lysstyrke"] == 0


def test_utelat_i_ett_rom_beholder_de_andres():
    import asyncio
    f = _flyt({}, utelat={"kveld": ["light.kjokken_benk"]}, rom_valgt="stue")
    svar = {_felt("light.stue_tak"): FOLG_ROLLEN, _felt("light.stue_gulv"): FOLG_ROLLEN,
            "utelat": ["light.stue_gulv"]}
    data = asyncio.get_event_loop().run_until_complete(f.async_step_lys(svar))
    u = data[CONF_UTELAT]["kveld"]
    assert "light.kjokken_benk" in u and "light.stue_gulv" in u


def test_alle_rom_ser_alle_lysene():
    import asyncio
    f = _flyt({}, rom_valgt="alle")
    svar = {_felt("light.stue_tak"): 30, _felt("light.kjokken_benk"): 80,
            "utelat": [], "ekstra": []}
    data = asyncio.get_event_loop().run_until_complete(f.async_step_lys(svar))
    rad = data[CONF_OVERSTYR]["kveld"]
    assert set(rad) == {"light.stue_tak", "light.kjokken_benk"}
