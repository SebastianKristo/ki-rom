"""Hvorfor et lys ikke blir slått av i nattmodus."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from custom_components.ki_rom.coordinator import LysMotor


def _koord(tilstander, overgang=2):
    # `overgang` er en property uten setter, så vi legger inn oppsettet den leser fra
    k = object.__new__(LysMotor)
    k.hass = MagicMock()
    k.hass.states.get.side_effect = lambda e: tilstander.get(e)
    # `oppsett` og `overgang` er properties uten setter — oppsettet kommer fra entry
    k.entry = SimpleNamespace(data={"overgang": overgang}, options={})
    k.kall = []

    async def _kall(domene, tjeneste, data, blocking=False):
        k.kall.append((domene, tjeneste, data))

    k.hass.services.async_call = _kall
    return k


def _st(features=0):
    return SimpleNamespace(attributes={"supported_features": features, "supported_color_modes": []})


def test_transition_bare_til_lys_som_stotter_det():
    """TRANSITION er bit 32. Sender vi «transition» til et lys uten den, avviser
    Home Assistant hele kallet — og lyset blir stående på."""
    t = {"light.med": _st(32), "light.uten": _st(0)}
    k = _koord(t)
    assert k._stotter_overgang("light.med")
    assert not k._stotter_overgang("light.uten")


def test_lys_uten_transition_slas_av_uten_parameteren():
    import asyncio
    t = {"light.uten": _st(0)}
    k = _koord(t)
    asyncio.get_event_loop().run_until_complete(k._sett_lys("light.uten", None))
    domene, tjeneste, data = k.kall[0]
    assert (domene, tjeneste) == ("light", "turn_off")
    assert "transition" not in data, data


def test_lys_med_transition_beholder_den():
    import asyncio
    t = {"light.med": _st(32)}
    k = _koord(t)
    asyncio.get_event_loop().run_until_complete(k._sett_lys("light.med", None))
    assert k.kall[0][2]["transition"] == 2


def test_lys_pa_bryter_kalles_i_sitt_eget_domene():
    """`light.turn_off` treffer ikke en switch-entitet. Den må kalles som switch."""
    import asyncio
    t = {"switch.stuelampe": _st(0)}
    k = _koord(t)
    asyncio.get_event_loop().run_until_complete(k._sett_lys("switch.stuelampe", None))
    assert k.kall[0][0] == "switch"
    assert k.kall[0][1] == "turn_off"
    assert "transition" not in k.kall[0][2]


def test_bryterlys_far_ikke_lysstyrke():
    """En bryter kan bare av og på — brightness_pct ville fått kallet avvist."""
    import asyncio
    t = {"switch.stuelampe": _st(0)}
    k = _koord(t)
    asyncio.get_event_loop().run_until_complete(k._sett_lys("switch.stuelampe", (40, 2700)))
    domene, tjeneste, data = k.kall[0]
    assert (domene, tjeneste) == ("switch", "turn_on")
    assert set(data) == {"entity_id"}, data
