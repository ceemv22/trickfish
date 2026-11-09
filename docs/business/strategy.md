# Trickfish: poslovna strategija

Vlasnik: @Ceemv22. Operativno vodi Claude (CEO/CTO). Ažurirano 2026-11-08.

## Jedna rečenica

**Stockfish nalazi najbolji potez. Trickfish nalazi potez na kojem će tvoj protivnik pogriješiti.**

## Pravila igre

1. **SentinelPay je glavni posao.** Trickfish od vlasnika traži najviše 1–2 sata tjedno, i to samo za stvari koje mora napraviti čovjek: račune, objave, isplate.
2. **Prodajemo samo ono što su potvrdili stvarni podaci.** Svaka zamka mora proći dvije provjere: Stockfish (potez je objektivno ispravan) i stvarne Lichess partije u ciljanom rejtingu (protivnici stvarno griješe). Brojke u marketingu dolaze ravno iz tih podataka.
3. **Engine je zamrznut.** C++ jezgra je gotova kao istraživački projekt. Nema novog rada na snazi enginea dok to ne zatraži kupac koji plaća.
4. **Workbook ostaje na Gumroadu za 9 $**, bez novog razvoja.

## Proizvodi po fazama

| Faza | Proizvod | Cijena | Uvjet za sljedeću fazu |
| --- | --- | --- | --- |
| 1 | Trap Packovi (PDF + PGN + vježbe) po otvaranju i rejtingu | 14 $ po paketu, komplet 3 paketa 29 $ | 10+ prodaja prvog paketa u 4 tjedna |
| 2 | Web aplikacija "tvoj izvještaj o zamkama" (Lichess nick → osobne zamke) | besplatno / 6 $ mjesečno | 300+ pratitelja ili 50+ prodaja paketa |
| 3 | Licenciranje podataka o zamkama trenerima i YouTuberima | po dogovoru | dolazni upiti |

## Kanal: X (@trickfishchess)

Format "zamka dana": slika pozicije uz pitanje "X % igrača 1200–1600 pogriješi ovdje. Bi li ti?", a dan kasnije odgovor uz link na paket. Kartice se generiraju automatski (`trickfish.trappack_render`). Postovi su u `x-launch-kit.md`.

## Mjerenje (svaki tjedan)

Pratitelji, impresije najboljeg posta, klikovi na Gumroad, prodaje, povrati novca. Što je nepoznato ostaje nepoznato.

## Kriterij za odustajanje

Ako prvi paket nakon 4 tjedna redovitog objavljivanja ima manje od 10 prodaja, mijenjamo jednu stvar (otvaranje, rejting ili cijenu) i pokušavamo još 4 tjedna. Ako ni nakon toga nema 10 prodaja, Trickfish ostaje hobi.

## Pipeline paketa

```bash
# 1. Izvući partije zadanog rejtinga iz javne Lichess baze (CC0)
curl -r 0-5000000000 https://database.lichess.org/standard/lichess_db_standard_rated_2026-10.pgn.zst \
  | zstd -dc | python -m trickfish.lichess_db --low 1200 --high 1599 --output band.tsv.gz
# 2. Pronaći zamke (Stockfish + statistika stvarnih partija)
python -m trickfish.trappack --moves "e4 e5" --color white --games band.tsv.gz --output traps.json
# 3. Iscrtati PDF, PGN i kartice za X
python -m trickfish.trappack_render traps.json --notes notes.json --output dist/pack
```
