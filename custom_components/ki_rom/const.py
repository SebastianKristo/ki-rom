"""Konstanter for KI Rom."""

DOMAIN = "ki_rom"
NAVN = "KI Rom"

CONF_AREAS = "areas"
CONF_EXCLUDE = "exclude"
CONF_INCLUDE_CATEGORY = "include_category"
CONF_INCLUDE_GROUPS = "include_groups"

# Domener som telles per rom
TRACKED_DOMAINS = ("light", "media_player", "switch", "binary_sensor", "sensor")

# binary_sensor-device_classes som regnes som "aktiv/stille"-sensorer
ACTIVE_BINARY_CLASSES = {
    "motion",
    "occupancy",
    "presence",
    "moving",
    "vibration",
    "door",
    "window",
    "opening",
    "garage_door",
    "sound",
}

# Sensortyper som lages per rom
KIND_LYS = "lys"
KIND_MEDIA = "media"
KIND_BRYTERE = "brytere"
KIND_SENSORER = "sensorer"
KIND_EFFEKT = "effekt"

KINDS = (KIND_LYS, KIND_MEDIA, KIND_BRYTERE, KIND_SENSORER, KIND_EFFEKT)

KIND_META = {
    KIND_LYS: {
        "navn": "Lys",
        "icon": "mdi:lightbulb-group-outline",
        "domain": "light",
        "aktiv_states": {"on"},
        "inaktiv_states": {"off"},
        "ord_aktiv": "på",
        "ord_inaktiv": "av",
    },
    KIND_MEDIA: {
        "navn": "Media",
        "icon": "mdi:speaker",
        "domain": "media_player",
        "aktiv_states": {"playing"},
        "inaktiv_states": {"off", "idle", "paused", "standby", "on"},
        "ord_aktiv": "spiller",
        "ord_inaktiv": "av",
    },
    KIND_BRYTERE: {
        "navn": "Brytere",
        "icon": "mdi:toggle-switch-outline",
        "domain": "switch",
        "aktiv_states": {"on"},
        "inaktiv_states": {"off"},
        "ord_aktiv": "på",
        "ord_inaktiv": "av",
    },
    KIND_SENSORER: {
        "navn": "Sensorer",
        "icon": "mdi:motion-sensor",
        "domain": "binary_sensor",
        "aktiv_states": {"on"},
        "inaktiv_states": {"off"},
        "ord_aktiv": "aktiv",
        "ord_inaktiv": "stille",
    },
    KIND_EFFEKT: {
        "navn": "Effekt",
        "icon": "mdi:flash",
        "domain": "sensor",
    },
}

TOTALT_ID = "totalt"
TOTALT_NAVN = "Hele huset"
