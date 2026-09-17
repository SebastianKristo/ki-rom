# KI Rom 2.3.1

## «Scener per rom» og «Overstyr lys i en scene» ga en tom feildialog

Begge stegene hentet lysmotoren slik:

```python
motor = next(iter(self.hass.data.get(DOMAIN, {}).values()), None)
... motor.rom ...
```

Men oppføringen i `hass.data` er ikke motoren — det er en `KiRomData` med `.hub` og
`.lys`. `motor.rom` kastet derfor `AttributeError`, og Home Assistant viser en tom
«Feil»-dialog når et konfigurasjonssteg kaster.

Fem steder gjorde dette, og de går nå gjennom én hjelper som pakker ut `.lys` hvis den
finnes, og ellers bruker objektet som det er. Da virker det også om formen endres senere.

Dette var ikke nytt i 2.3.0 — begge menyvalgene har vært døde siden `KiRomData` ble
innført. At det ble oppdaget nå, er fordi 2.3.0 gjorde det verdt å gå inn i dem.

Tre tester dekker de tre formene oppføringen kan ha: pakket i `KiRomData`, motoren
direkte, og ingen oppføring i det hele tatt. De eksisterende testene er rettet til den
formen som faktisk er i bruk — de brukte motoren direkte, og ville derfor ikke fanget
feilen.

---

# KI Rom 2.3.0

## Finjuster scener per rom

«Finjuster en scene» listet før hvert lys i hele huset for den valgte scenen. Nå velger du
rommet først, så scenen, og skjemaet viser bare lysene i det rommet: «Kveld i Stue».
«Alle rom» finnes fortsatt.

Glidebryteren betyr det samme: −1 lar rollen bestemme, 0 slår lyset av i scenen, og 1–100
er lysstyrke i prosent.

Overstyringene for lys som ikke vises beholdes når du lagrer. Uten det ville redigering av
stua slettet alt du hadde satt i de andre rommene.
