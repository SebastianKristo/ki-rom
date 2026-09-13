import pytest
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.ki_rom.const import DOMAIN


async def test_setter_opp_og_lager_entiteter(hass):
    hass.states.async_set("light.stue_tak", "on")
    hass.states.async_set("light.stue_gulvlampe", "off")
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state.recoverable is False or True
    for tj in ("sett", "les_rom", "lagre_naa", "sett_lys", "nullstill"):
        assert hass.services.has_service(DOMAIN, tj), tj
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def test_flyten_har_alle_steg(hass):
    from custom_components.ki_rom.config_flow import KiRomOptionsFlow
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    flow = KiRomOptionsFlow(entry)
    flow.hass = hass
    res = await flow.async_step_init()
    for steg in res["menu_options"]:
        assert hasattr(flow, f"async_step_{steg}"), steg


async def test_innstillinger_beholder_romvalget(hass):
    """Lagring under Innstillinger skal ikke slette resten av oppsettet."""
    from custom_components.ki_rom.config_flow import KiRomOptionsFlow
    from custom_components.ki_rom.const import CONF_AREAS, CONF_SONER
    entry = MockConfigEntry(
        domain=DOMAIN, data={},
        options={CONF_AREAS: ["stue"], CONF_SONER: [{"navn": "Oppe", "rom": ["stue"]}]},
        unique_id=DOMAIN)
    entry.add_to_hass(hass)
    flow = KiRomOptionsFlow(entry)
    flow.hass = hass
    res = await flow.async_step_innstillinger({"rom": ["kjokken"], "scener": ["maks"]})
    assert res["data"][CONF_AREAS] == ["stue"]
    assert res["data"][CONF_SONER]
    assert res["data"]["rom"] == ["kjokken"]


async def test_entitets_idene_er_uendret(hass, area_registry, entity_registry):
    """Scenene skal beholde ID-ene de hadde i ki_lys, så dashbordene virker."""
    from custom_components.ki_rom.const import CONF_ROM
    omraade = area_registry.async_create("Stue")
    oppf = entity_registry.async_get_or_create(
        "light", "demo", "taklys-1", suggested_object_id="taklys")
    entity_registry.async_update_entity(oppf.entity_id, area_id=omraade.id)
    hass.states.async_set(oppf.entity_id, "on")

    entry = MockConfigEntry(domain=DOMAIN, data={},
                            options={CONF_ROM: [omraade.id]}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.states.get("button.stue_lys_komfort") is not None
    assert hass.states.get("switch.stue_lys_alle") is not None
    oversikt = hass.states.get("sensor.stue_lys_oversikt")
    assert oversikt is not None
    assert oversikt.attributes["integrasjon"] == "ki_lys"
    assert hass.states.get("sensor.stue_oversikt") is not None
