# Prvi Trickfish demo

Ovaj vodič koristi postojeće rezultate, bez izmišljene preporuke za konkretnog kupca. Paket je materijal za stručni pregled, a ne dovršena turnirska priprema.

## Redoslijed za 15 minuta

1. Pitati koje otvaranje i protivnike trener stvarno priprema. Pokazati poziciju nakon 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 i zabilježiti njegov prvi izbor prije otkrivanja rangiranja.
2. Otvoriti `expert-review/quiet-italian/worksheet.md` i oba PGN izvoza. Kandidat je 4.c3, objektivna polazna opcija 4.d4. Zabilježeni gubitak je 19 cp na dubini 12, a razlika modeliranih očekivanja 75,81 cp. To nisu postotci pobjede niti dokaz ljudske koristi.
3. Pregledati obranu nakon 4.c3 i pitati što trener smatra poučnim, slabim ili nedovoljno provjerenim. Probabilitet odgovora dolazi iz modela, ne iz novog pokusa na igračima.
4. Otvoriti i početnu poziciju te Scholar obranu. Pokazati slučajeve bez kvalificirane alternative i promjene izbora. Ne predstavljati jedan kandidat od pet kao stopu uspješnosti.
5. Zatražiti kritiku i popuniti prazni feedback tek stvarnim odgovorima. Ako postoji interes, ponuditi pet vlastitih pozicija prema priloženom nacrtu ponude.

## Dokazi i granice

Kontrolirani Linux run [41913607427](https://github.com/ceemv22/trickfish/actions/runs/41913607427) pripada commitu c51dffc i Stockfishu 19. Raniji run sa Stockfishom 16 nije našao kvalificirani kandidat. Naknadna lokalna usporedba kontroliranih Windows i Linux rezultata podudarala je deset analiza na provjerenim poljima; to ne znači bitnu identičnost izvršavanja, neovisnu šahovsku potvrdu ni učinak na igrače.

Python CI za unos vlastitog repertoara na commitu 137d2cc prošao je u [runu 41978100904](https://github.com/ceemv22/trickfish/actions/runs/41978100904). Taj run ne predstavlja novu realnu Stockfish/Maia analizu.

Paket uključuje izvorne analize, zabilježene kriterije i prazne obrasce. Vanjski engine i model ne distribuiraju se u demo paketu. Nema svjedočanstava kupaca, potvrđene uštede vremena ni ostvarenog prihoda.
