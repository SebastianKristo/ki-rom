"""Konstanter for KI Rom."""

DOMAIN = "ki_rom"
NAVN = "KI Rom"

# Kortene ute i dashbordet kjenner lysscenene og julelysene på attributtet
# `integrasjon: ki_lys`. Entitetene beholder den markøren etter sammenslåingen –
# både lysscenene og jul-entitetene – så ingen kort må endres.
LYS_MARKOR = "ki_lys"

CONF_AREAS = "areas"
CONF_EXCLUDE = "exclude"
CONF_EKSKLUDER_ROM = "ekskluder_rom"   # rom som holdes helt utenfor (tellere og lysscener)
CONF_INCLUDE_CATEGORY = "include_category"
CONF_INCLUDE_GROUPS = "include_groups"

# Domener som telles per rom
TRACKED_DOMAINS = (
    "light",
    "media_player",
    "switch",
    "binary_sensor",
    "sensor",
    "climate",
    "cover",
    "fan",
    "script",
    "scene",
)

# sensor-device_classes som tas med
SENSOR_CLASSES = {"power", "temperature", "humidity", "illuminance"}

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
KIND_OVERSIKT = "oversikt"

KINDS = (KIND_LYS, KIND_MEDIA, KIND_BRYTERE, KIND_SENSORER, KIND_EFFEKT, KIND_OVERSIKT)

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
    KIND_OVERSIKT: {
        "navn": "Oversikt",
        "icon": "mdi:floor-plan",
        "domain": None,
    },
}

TOTALT_ID = "totalt"
TOTALT_NAVN = "Hele huset"


# =====================================================================
# Lysscener (tidligere den egne integrasjonen ki_lys)
# =====================================================================
CONF_ROM = "rom"                  # liste med area_id
CONF_EKSKLUDER = "ekskluder"      # lys som ikke skal være med
CONF_SCENER = "scener"            # hvilke scener som lages (standard for alle rom)
CONF_SCENER_ROM = "scener_rom"    # {area_id: [scene]} – eget utvalg per rom
CONF_SONER = "soner"              # [{navn, rom: [area_id], skjul_enkeltrom}] – flere rom som ett
CONF_EGNE = "egne"                # egne scener lagt til manuelt
CONF_OVERGANG = "overgang"        # sekunder på dimmingen
CONF_NATTLYS = "nattlys"          # lys som får stå på i nattmodus
CONF_OVERSTYR = "overstyr"        # {scene: {entity_id: {paa, lysstyrke, kelvin}}}
CONF_UTELAT = "utelat"            # {scene: [entity_id]} – lys som ikke er med i scenen
CONF_EKSTRA_LYS = "ekstra_lys"    # {scene: [entity_id]} – lys utenfra som skal med

FOLG_ROLLEN = -1                  # lysstyrke -1 betyr «la rollen bestemme»

# ---------------------------------------------------------------- julelys
CONF_JUL = "jul"                  # {aktiv, grupper, fra, til, maal, varsler}
STD_JUL_FRA = "11-01"             # julesesongen slås på
STD_JUL_TIL = "03-01"             # og av igjen
STD_JUL_MAAL = "12-24"            # nedtellingen går mot julaften

# Gruppene i julepopupen: navn, ikon og hvordan de gjenkjennes
JUL_GRUPPER = [
    ("stjerner", "Julestjerner", "mdi:star-four-points", r"stjerne"),
    ("staker", "Julestaker", "mdi:candelabra-fire", r"stake|lysestake"),
    ("ute", "Utendørs", "mdi:string-lights", r"slynge|ute|veranda|hage|inngang"),
    ("annet", "Annet julelys", "mdi:string-lights", r""),
]

STD_OVERGANG = 2

ATTR_INTEGRASJON = "integrasjon"
ATTR_TYPE = "ki_type"

# Scenene som lages automatisk. rekkefølgen er den kortet viser dem i.
SCENER: dict[str, dict] = {
    "maks": {"navn": "Maks lys", "ikon": "mdi:lightbulb-on", "rekkefolge": 1},
    "komfort": {"navn": "Komfort", "ikon": "mdi:sofa", "rekkefolge": 2},
    "middag": {"navn": "Middag", "ikon": "mdi:silverware-fork-knife", "rekkefolge": 3},
    "tv": {"navn": "TV-kveld", "ikon": "mdi:television-classic", "rekkefolge": 4},
    "mindre": {"navn": "Mindre lys", "ikon": "mdi:lightbulb-on-40", "rekkefolge": 5},
    "natt": {"navn": "Nattmodus", "ikon": "mdi:weather-night", "rekkefolge": 6},
    "av": {"navn": "Alt av", "ikon": "mdi:lightbulb-off", "rekkefolge": 7},
}

STD_SCENER = list(SCENER)

# Hvor kraftig hver rolle lyser i hver scene: (lysstyrke i %, fargetemperatur i kelvin).
# None betyr at lyset slås av.
OPPSKRIFT: dict[str, dict[str, tuple[int, int] | None]] = {
    "maks":    {"tak": (100, 4000), "lampe": (100, 3500), "stemning": (100, 3000), "arbeid": (100, 4000), "nattlys": (60, 2200)},
    "komfort": {"tak": (60, 2900),  "lampe": (70, 2700),  "stemning": (80, 2400),  "arbeid": (70, 3500),  "nattlys": (40, 2200)},
    "middag":  {"tak": (45, 2700),  "lampe": (60, 2500),  "stemning": (75, 2300),  "arbeid": None,        "nattlys": (30, 2200)},
    "tv":      {"tak": None,        "lampe": (25, 2300),  "stemning": (55, 2200),  "arbeid": None,        "nattlys": (25, 2200)},
    "mindre":  {"tak": (25, 2500),  "lampe": (30, 2400),  "stemning": (35, 2300),  "arbeid": (30, 2700),  "nattlys": (20, 2200)},
    "natt":    {"tak": None,        "lampe": None,        "stemning": None,        "arbeid": None,        "nattlys": (8, 2200)},
    "av":      {"tak": None,        "lampe": None,        "stemning": None,        "arbeid": None,        "nattlys": None},
}

# Nøkkelord som avgjør hvilken rolle et lys får.
ROLLER: list[tuple[str, str]] = [
    ("nattlys", r"natt|nightlight|nattlampe|seng"),
    # «benk» alene treffer også «tv_benk», derfor bare de sammensatte formene
    ("arbeid",  r"pult|kjokkenbenk|kjøkkenbenk|arbeidsbenk|benkebelysning|arbeid|skrivebord|speil|desk"),
    ("stemning", r"stripe|strip|led|list|bak|hylle|skap|gulv|vindu|stemning|ambient|wled"),
    ("lampe",   r"lampe|bord|gulvlampe|pendel|vegg|lamp"),
    ("tak",     r"tak|ceiling|spot|downlight|himling"),
]
STD_ROLLE = "lampe"
