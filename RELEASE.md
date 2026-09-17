# KI Rom 2.3.0

## Finjuster scener per rom

«Finjuster en scene» listet før hvert lys i hele huset for den valgte scenen. Med tolv rom
blir det en side med tretti glidebrytere, og stua er umulig å finne i den.

Nå velger du **rommet først**, så scenen. Skjemaet viser bare lysene i det rommet, med
navnet på rommet i overskriften: «Kveld i Stue». «Alle rom» finnes fortsatt for den som
vil se alt på én side.

Glidebryteren betyr det samme som før: −1 lar rollen bestemme, 0 slår lyset av i scenen,
og 1–100 er lysstyrke i prosent.

## Feilen det avdekket

Steget skrev hele scenen på nytt ut fra feltene på skjermen. Så snart lista er filtrert
til ett rom, ville det å lagre stua slettet alt du hadde satt i de andre rommene — og det
uten noe varsel.

Overstyringene for lys som ikke vises beholdes nå. Det samme gjelder «lys som ikke er med
i scenen»: redigerer du ett rom, er det bare rommets egne lys som legges til eller fjernes
fra lista, resten står urørt.

Lys utenfra som skal med i en scene hører ikke til et enkelt rom, så det feltet vises bare
under «Alle rom».

Fem tester dekker dette: at ett rom ikke overskriver et annet, at −1 fjerner
overstyringen, at 0 slår lyset av, at utelatelser i andre rom beholdes, og at «Alle rom»
ser alle lysene.
