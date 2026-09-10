"""Hub for KI Rom – kobler entiteter til rom og teller status."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ACTIVE_BINARY_CLASSES,
    CONF_AREAS,
    CONF_EXCLUDE,
    CONF_INCLUDE_CATEGORY,
    CONF_INCLUDE_GROUPS,
    DOMAIN,
    KIND_EFFEKT,
    KIND_META,
    KIND_OVERSIKT,
    SENSOR_CLASSES,
    TOTALT_ID,
    TRACKED_DOMAINS,
)

_LOGGER = logging.getLogger(__name__)


def signal(entry_id: str, area_id: str) -> str:
    """Dispatcher-signal for ett rom."""
    return f"{DOMAIN}_{entry_id}_{area_id}"


class KiRomHub:
    """Holder oversikt over hvilke entiteter som hører til hvilket rom."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.areas: dict[str, str] = {}  # area_id -> navn
        self.area_icons: dict[str, str | None] = {}
        self.members: dict[str, dict[str, list[str]]] = {}  # area_id -> domain -> [entity_id]
        self._entity_area: dict[str, str] = {}
        self._device_of: dict[str, str | None] = {}  # entity_id -> device_id
        self._class_of: dict[str, str | None] = {}  # entity_id -> device_class
        self._unsub_state = None
        self._unsub_registry: list = []
        self._known_area_ids: set[str] | None = None
        self._debouncer = Debouncer(
            hass,
            _LOGGER,
            cooldown=2.0,
            immediate=False,
            function=self._async_rebuild,
        )

    # ------------------------------------------------------------------ oppsett

    @property
    def options(self) -> dict[str, Any]:
        return {**self.entry.data, **self.entry.options}

    async def async_start(self) -> None:
        self._build()
        self._known_area_ids = set(self.areas)
        self._subscribe_states()
        for event_type in (
            ar.EVENT_AREA_REGISTRY_UPDATED,
            er.EVENT_ENTITY_REGISTRY_UPDATED,
            dr.EVENT_DEVICE_REGISTRY_UPDATED,
        ):
            self._unsub_registry.append(
                self.hass.bus.async_listen(event_type, self._registry_changed)
            )

    @callback
    def async_stop(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        for unsub in self._unsub_registry:
            unsub()
        self._unsub_registry = []
        self._debouncer.async_cancel()

    @callback
    def _registry_changed(self, _event: Event) -> None:
        self._debouncer.async_schedule_call()

    async def _async_rebuild(self) -> None:
        self._build()
        new_ids = set(self.areas)
        if self._known_area_ids is not None and new_ids != self._known_area_ids:
            _LOGGER.info("KI Rom: rom endret, laster på nytt")
            self._known_area_ids = new_ids
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)
            return
        self._subscribe_states()
        self._notify_all()

    # ------------------------------------------------------------------ kartlegging

    def _build(self) -> None:
        area_reg = ar.async_get(self.hass)
        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)

        wanted = set(self.options.get(CONF_AREAS) or [])
        excluded = set(self.options.get(CONF_EXCLUDE) or [])
        include_category = bool(self.options.get(CONF_INCLUDE_CATEGORY, False))
        include_groups = bool(self.options.get(CONF_INCLUDE_GROUPS, False))

        areas: dict[str, str] = {}
        icons: dict[str, str | None] = {}
        for area in area_reg.async_list_areas():
            if wanted and area.id not in wanted:
                continue
            areas[area.id] = area.name
            icons[area.id] = area.icon

        members: dict[str, dict[str, list[str]]] = {
            aid: defaultdict(list) for aid in areas
        }
        device_of: dict[str, str | None] = {}
        class_of: dict[str, str | None] = {}

        for entry in ent_reg.entities.values():
            if entry.platform == DOMAIN:
                continue
            if entry.domain not in TRACKED_DOMAINS:
                continue
            if entry.disabled or entry.hidden:
                continue
            if entry.entity_id in excluded:
                continue
            if entry.entity_category is not None and not include_category:
                continue
            if entry.platform == "group" and not include_groups and entry.domain != "cover":
                # cover-grupper beholdes: de brukes som "master" for gardiner
                continue

            area_id = entry.area_id
            if not area_id and entry.device_id:
                device = dev_reg.async_get(entry.device_id)
                if device:
                    area_id = device.area_id
            if not area_id or area_id not in members:
                continue

            device_class = entry.device_class or entry.original_device_class
            if entry.domain == "sensor" and device_class not in SENSOR_CLASSES:
                continue
            if entry.domain == "binary_sensor" and device_class not in ACTIVE_BINARY_CLASSES:
                continue

            members[area_id][entry.domain].append(entry.entity_id)
            device_of[entry.entity_id] = entry.device_id
            class_of[entry.entity_id] = str(device_class) if device_class else None

        for domains in members.values():
            for lst in domains.values():
                lst.sort()

        self.areas = dict(sorted(areas.items(), key=lambda kv: kv[1].lower()))
        self.area_icons = icons
        self.members = members
        self._device_of = device_of
        self._class_of = class_of
        self._entity_area = {
            eid: aid
            for aid, domains in members.items()
            for lst in domains.values()
            for eid in lst
        }

    def _subscribe_states(self) -> None:
        if self._unsub_state:
            self._unsub_state()
            self._unsub_state = None
        ids = sorted(self._entity_area)
        if ids:
            self._unsub_state = async_track_state_change_event(
                self.hass, ids, self._state_changed
            )

    @callback
    def _state_changed(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        area_id = self._entity_area.get(entity_id)
        if area_id:
            async_dispatcher_send(self.hass, signal(self.entry.entry_id, area_id))
        async_dispatcher_send(self.hass, signal(self.entry.entry_id, TOTALT_ID))

    @callback
    def _notify_all(self) -> None:
        for area_id in list(self.areas) + [TOTALT_ID]:
            async_dispatcher_send(self.hass, signal(self.entry.entry_id, area_id))

    # ------------------------------------------------------------------ oppslag

    def entity_ids(self, area_id: str | None, domain: str) -> list[str]:
        """Entiteter i et rom (None/'totalt' = hele huset)."""
        if area_id in (None, TOTALT_ID):
            out: list[str] = []
            for domains in self.members.values():
                out.extend(domains.get(domain, []))
            return sorted(out)
        return list(self.members.get(area_id, {}).get(domain, []))

    def sensors_of_class(self, area_id: str | None, device_class: str) -> list[str]:
        return [
            e
            for e in self.entity_ids(area_id, "sensor")
            if self._class_of.get(e) == device_class
        ]

    def _navn(self, entity_id: str) -> str:
        state = self.hass.states.get(entity_id)
        if state is None:
            return entity_id
        return state.attributes.get("friendly_name") or entity_id

    def compute(self, area_id: str | None, kind: str) -> dict[str, Any]:
        """Beregn verdi + attributter for en sensortype i et rom."""
        if kind == KIND_OVERSIKT:
            return self._compute_oversikt(area_id)
        if kind == KIND_EFFEKT:
            return self._compute_effekt(self.sensors_of_class(area_id, "power"))

        meta = KIND_META[kind]
        ids = self.entity_ids(area_id, meta["domain"])

        aktiv: list[str] = []
        inaktiv: list[str] = []
        utilgjengelig: list[str] = []
        for eid in ids:
            state = self.hass.states.get(eid)
            if state is None or state.state in ("unavailable", "unknown"):
                utilgjengelig.append(eid)
            elif state.state in meta["aktiv_states"]:
                aktiv.append(eid)
            else:
                inaktiv.append(eid)

        return {
            "value": len(aktiv),
            "attrs": {
                "totalt": len(ids),
                "aktiv": len(aktiv),
                "inaktiv": len(inaktiv),
                "utilgjengelig": len(utilgjengelig),
                "tekst": f"{len(aktiv)} {meta['ord_aktiv']} - {len(inaktiv)} {meta['ord_inaktiv']}",
                "aktiv_liste": aktiv,
                "inaktiv_liste": inaktiv,
                "utilgjengelig_liste": utilgjengelig,
                "aktiv_navn": [self._navn(e) for e in aktiv],
                "entiteter": ids,
            },
        }

    def _compute_effekt(self, ids: list[str]) -> dict[str, Any]:
        total = 0.0
        per: dict[str, float] = {}
        for eid in ids:
            state = self.hass.states.get(eid)
            if state is None or state.state in ("unavailable", "unknown", ""):
                continue
            try:
                val = float(state.state)
            except (TypeError, ValueError):
                continue
            unit = (state.attributes.get("unit_of_measurement") or "W").strip()
            if unit.lower() == "kw":
                val *= 1000.0
            elif unit.lower() == "mw":
                val /= 1000.0
            per[eid] = round(val, 1)
            total += val
        total = round(total, 1)
        return {
            "value": total,
            "attrs": {
                "tekst": f"{total:.0f} W",
                "kilder": per,
                "entiteter": ids,
            },
        }

    def _linked_power(self, area_id: str | None, entity_id: str) -> str | None:
        """Finn effektsensor på samme enhet som entiteten (bryter, klima, vifte)."""
        dev = self._device_of.get(entity_id)
        if not dev:
            return None
        for sensor in self.sensors_of_class(area_id, "power"):
            if self._device_of.get(sensor) == dev:
                return sensor
        return None

    def _compute_oversikt(self, area_id: str | None) -> dict[str, Any]:
        """Alt kortet trenger for å auto-bygge en rom-popup."""
        aid = area_id or TOTALT_ID
        power_all = self.sensors_of_class(area_id, "power")

        def with_power(ids: list[str]) -> list[dict[str, Any]]:
            return [
                {"entity": e, "effekt": self._linked_power(area_id, e)} for e in ids
            ]

        brytere = with_power(self.entity_ids(area_id, "switch"))
        klima = with_power(self.entity_ids(area_id, "climate"))
        vifter = with_power(self.entity_ids(area_id, "fan"))
        brukt = {d["effekt"] for d in brytere + klima + vifter if d["effekt"]}

        lys = self.entity_ids(area_id, "light")
        media = self.entity_ids(area_id, "media_player")
        gardiner = self.entity_ids(area_id, "cover")
        sensorer = [
            {"entity": e, "klasse": self._class_of.get(e)}
            for e in self.entity_ids(area_id, "binary_sensor")
        ]
        skript = self.entity_ids(area_id, "script")
        scener = self.entity_ids(area_id, "scene")

        attrs: dict[str, Any] = {
            "integrasjon": DOMAIN,
            "area_id": aid,
            "ikon": self.area_icons.get(aid),
            "lys": lys,
            "media": media,
            "brytere": brytere,
            "vifter": vifter,
            "klima": klima,
            "gardiner": gardiner,
            "sensorer": sensorer,
            "skript": skript,
            "scener": scener,
            "temperatur": self.sensors_of_class(area_id, "temperature"),
            "fuktighet": self.sensors_of_class(area_id, "humidity"),
            "lysniva": self.sensors_of_class(area_id, "illuminance"),
            "effekt": power_all,
            "effekt_andre": [e for e in power_all if e not in brukt],
        }
        total = (
            len(lys)
            + len(media)
            + len(brytere)
            + len(vifter)
            + len(klima)
            + len(gardiner)
            + len(sensorer)
        )
        return {"value": total, "attrs": attrs}
