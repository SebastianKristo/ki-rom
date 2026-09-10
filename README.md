# KI Rom

Custom integration for Home Assistant som automatisk lager tellersensorer for **hvert rom (område)** i HA.
Erstatter JS-templatene i expander-headerne (`Lys – 3 på - 5 av`, `Enheter – 412 W`, `Sensorer – 1 aktiv - 5 stille`).

## Sensorer

For hvert rom (device = rommet, plassert i rommet automatisk) og for «Hele huset»:

| Entitet | Verdi | Attributter |
|---|---|---|
| `sensor.<rom>_lys` | antall lys **på** | `totalt`, `aktiv`, `inaktiv`, `utilgjengelig`, `tekst` («3 på - 5 av»), `aktiv_liste`, `inaktiv_liste`, `aktiv_navn`, `entiteter` |
| `sensor.<rom>_media` | antall media_player som **spiller** | samme, `tekst` = «1 spiller - 2 av» |
| `sensor.<rom>_brytere` | antall switch **på** | samme |
| `sensor.<rom>_sensorer` | antall binary_sensor **aktiv** (motion/occupancy/presence/door/window/opening/vibration …) | samme, `tekst` = «1 aktiv - 5 stille» |
| `sensor.<rom>_effekt` | sum W av alle power-sensorer i rommet | `tekst` («412 W»), `kilder` (W per entitet) |
| `sensor.<rom>_oversikt` | antall entiteter i rommet | `lys`, `media`, `brytere` (+effektsensor), `vifter`, `klima` (+effektsensor), `gardiner`, `sensorer` (+klasse), `skript`, `scener`, `temperatur`, `fuktighet`, `lysniva`, `effekt`, `area_id`, `ikon`, `etasje`/`etasje_niva` (fra HA-etasjer) – brukes av `ki-rom-card` til å auto-bygge popupen |

Totaler: `sensor.hele_huset_lys`, `sensor.hele_huset_effekt` osv.

Entiteter kobles til rom via entitetens område, ellers via enhetens område – samme logikk som JS-koden.
Deaktiverte/skjulte entiteter, konfig-/diagnose-entiteter (status-LED på UniFi/ESPHome) og grupper hoppes over som standard.

## Automatisk

- Tomt romvalg = alle rom. Nye rom i HA gir nye sensorer automatisk (integrasjonen laster seg selv på nytt).
- Flytter du en enhet til et annet rom, oppdateres tellingen uten omstart.
- Innstillinger → Integrasjoner → KI Rom → Konfigurer: velg rom, ignorer entiteter (f.eks. `light.kjokken_spot_1/2` som er del av en gruppe), ta med grupper/kategori-entiteter.

## Installasjon

HACS → Custom repositories → `SebastianKristo/ki-rom` (Integration), eller kopier `custom_components/ki_rom` til `config/custom_components/`. Restart HA, legg til «KI Rom».

## Dashboard

Se `examples/expander-header.yaml`. Kort fortalt – bytt ut JS-blokkene i expander-headerne med:

```yaml
- type: custom:button-card
  entity: sensor.stue_lys
  name: "[[[ return entity.attributes.tekst ]]]"
```

eller helt uten JS:

```yaml
- type: custom:button-card
  entity: sensor.stue_lys
  show_name: false
  show_state: true
  state_display: "[[[ return entity.attributes.tekst ]]]"
```

(button-card er allerede i bruk i dashbordet; alternativt `type: markdown` med `{{ state_attr('sensor.stue_lys','tekst') }}`.)
