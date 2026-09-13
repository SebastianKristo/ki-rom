# KI Rom 2.0.0 — KI Lys er slått inn i KI Rom

`ki_lys` finnes ikke lenger som egen integrasjon. Lysscenene, sonene og julelyset ligger
nå i `ki_rom`, som allerede eide romlista. Ett oppsett, én romliste, ett sted å velge bort
entiteter.

## Slik oppgraderer du

1. **Fjern KI Lys først**, i denne rekkefølgen: Innstillinger → Enheter og tjenester →
   KI Lys → de tre prikkene → Slett. Slett deretter `custom_components/ki_lys/`.
   Fjerner du mappa uten å slette oppsettet, blir entitetene liggende foreldreløse i
   registeret; KI Rom rydder dem da bort ved oppstart, men det er ryddigere å ta det selv.
2. Legg inn `custom_components/ki_rom/` (2.0.0) og start HA på nytt.
3. Åpne KI Rom → Innstillinger. Menyen har fått **Rom og tellere** øverst; resten av
   menyen er lysoppsettet, uendret.

Lysoppsettet ditt ligger i den gamle oppføringen og følger ikke automatisk med. Sett rom,
soner, scener per rom og julelys på nytt én gang, så er det gjort.

## Entitets-ID-ene er uendret

`button.<rom>_lys_<scene>`, `switch.<rom>_lys_alle` og `sensor.<rom>_lys_oversikt` heter
det samme som før, og beholder attributtet `integrasjon: ki_lys`. Det er den markøren
ki-rom-card 1.12.0 kjenner scenene på, så ingen kort og ingen dashbord trenger endring.

## Rettet underveis

* **Innstillinger slettet resten av oppsettet.** `async_step_innstillinger` lagret med
  `data={**user_input, egne}`, altså uten soner, overstyringer, utelatte lys, ekstra lys,
  scener per rom og julelysoppsettet. Hver gang du åpnet Innstillinger og trykket lagre,
  forsvant alt dette. Alle stegene fletter nå inn i eksisterende options.
* **Kolliderende unique_id.** Romtellernes `sensor.<rom>_oversikt` og lysscenenes
  `sensor.<rom>_lys_oversikt` brukte begge `<entry>_<area>_oversikt`. Slått sammen ville
  HA droppet den ene med «does not generate unique IDs». Lysentitetene har nå `_lys_` i
  nøkkelen.

## Nytt

* Lar du romlista for lys stå tom, arves rommene fra **Rom og tellere**. Er også den tom,
  dekkes alle områder — samme regel begge steder.
* Entiteter du har valgt bort under Rom og tellere, holdes også utenfor lysscenene.

## Tester

`tests/test_merge.py` kjører oppsett mot et ekte HA-testoppsett og sjekker at tjenestene
registreres, at hvert menyvalg har et steg, at entitets-ID-ene og kortmarkøren er intakte,
og at lagring under Innstillinger ikke sletter romvalget.
