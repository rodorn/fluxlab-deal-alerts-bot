# Deal Alerts jako subskrypcja

Platny feed okazji dla lowcow arbitrazu. Silnik skanuje marketplace, ocenia
oferty wzgledem mediany rynkowej i wysyla tylko realne okazje (DEAL) na Discord
lub Telegram. Klient placi za czas: konto paid dostaje alert natychmiast, zanim
okazja zniknie.

## Nisza

Startujemy waskim segmentem, gdzie ceny sa plynne, a roznice duze:

- LEGO (sety wycofywane, promocje, retail vs rynek wtorny)
- sneakersy (limitowane dropy, restocki, roznice miedzy sklepami)

Model jest kategorio-agnostyczny, wiec kolejne nisze (elektronika, karty
graficzne, konsole) dokladamy bez przepisywania silnika.

## Dlaczego to dziala

- Przewaga to czas reakcji. Kto pierwszy widzi okazje, ten kupuje.
- Median-scoring odsiewa szum: alert leci tylko gdy cena realnie odstaje.
- Free tier buduje lejek, opoznienie 6 do 12h czyni paid oczywistym wyborem.

## Cennik

| Plan    | Cena       | Co dostajesz                                     |
| ------- | ---------- | ------------------------------------------------ |
| Free    | 0 zl       | alerty opoznione o 6 do 12h, 1 kategoria         |
| Starter | 39 zl / mc | alerty natychmiastowe, 1 nisza, Discord/Telegram |
| Pro     | 79 zl / mc | wszystkie nisze, priorytet, filtry progu profitu |

## Model biznesowy

- Subskrypcja miesieczna (Stripe Checkout), automatyczna aktywacja przez webhook
  `checkout.session.completed`.
- Koszt krancowy jednego subskrybenta bliski zeru: ten sam scan obsluguje cala
  liste odbiorcow.
- Wzrost przez spolecznosc (Discord), tresci pokazujace zrealizowane okazje oraz
  program polecen.
- Retencja oparta na dowodzie wartosci: podsumowanie "ile okazji w tym miesiacu"
  i szacowany zysk lowcy.

## Wdrozenie u klienta

1. Podpiecie zrodla i kalibracja progow pod nisze.
2. Kanaly Discord/Telegram + Stripe Checkout.
3. Free tier jako lejek, konwersja na paid.

---

by [FluxLab](https://fluxlab.pl)
