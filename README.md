# deal-alerts-bot

Silnik platnego feedu "deal alertow" dla arbitrazu na marketplace'ach. Pobiera
oferty z publicznego, bezkluczowego zrodla, ocenia je (scoring cena vs mediana
kategorii), a wykryte okazje (DEAL) wysyla na Discord/Telegram. Warstwa
subskrypcji rozdziela dostep: konto free dostaje alerty z opoznieniem, konto
paid natychmiast.

Silnik jest kategorio-agnostyczny. Nisza (np. LEGO, sneakersy) to kwestia
konfiguracji zrodla i progow, nie zmian w kodzie.

## Architektura

```
scrape (src/source.py) -> scoring (src/scoring.py) -> filtr DEAL
      -> notify wg tieru (src/notify.py, dostep z src/subscription.py)
```

- `src/source.py` interfejs `DealSource` + implementacja `SlickdealsSource`
  (publiczny RSS frontpage Slickdeals, bez logowania i klucza) oraz `DemoSource`
  (wbudowany przyklad, uzywany tez jako fallback gdy zrodlo zawodzi). Pola oferty:
  `title, price, currency, url, image, category, seen_at`.
- `src/scoring.py` liczy mediane ceny per kategoria i zapala flage DEAL, gdy cena
  jest o `min_discount` ponizej mediany lub ponizej absolutnego progu.
- `src/subscription.py` model uzytkownika w SQLite (email, tier free/paid,
  expires_at), sprawdzanie dostepu i placeholder integracji Stripe.
- `src/notify.py` wysylka na Discord/Telegram przez webhook z env; bez env jest
  no-op. Free tier = opoznienie (domyslnie 6 do 12h), paid = natychmiast.
- `run.py` spina caly przeplyw i pokazuje dzialanie w trybie demo.

## Szybki start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

python run.py                 # zrodlo live (Slickdeals) z fallbackiem demo
python run.py --source demo   # wymuszony tryb offline
pytest -q                     # testy
```

## Konfiguracja (zmienne srodowiskowe)

| Zmienna               | Opis                                              |
| --------------------- | ------------------------------------------------- |
| `DISCORD_WEBHOOK_URL` | webhook kanalu Discord (jesli ustawiony, uzywany) |
| `TELEGRAM_BOT_TOKEN`  | token bota Telegram                               |
| `TELEGRAM_CHAT_ID`    | id czatu/kanalu Telegram                          |

Bez zadnej z tych zmiennych powiadomienia dzialaja jako no-op (silnik i tak
przelicza okazje). Domyslnie `run.py` dziala w trybie `dry_run`; dodaj `--send`,
aby realnie wysylac.

## Integracja Stripe (placeholder)

`src/subscription.py` zawiera `handle_stripe_event(event, store)`, ktore obsluguje
mockowany event `checkout.session.completed` i aktywuje subskrypcje paid dla
emaila klienta. Dziala bez klucza Stripe (na samym slowniku eventu), dzieki czemu
caly przeplyw aktywacji jest testowalny.

Produkcyjny webhook to cienka warstwa HTTP nad ta funkcja:

```python
# pseudokod endpointu (np. FastAPI/Flask)
event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
handle_stripe_event(event, store)
```

Sekrety (klucz Stripe, endpoint secret, webhooki) trzymaj w env lub menedzerze
sekretow. Repo ich nie zawiera.

## Testy

`pytest -q` sprawdza scoring (flaga DEAL, progi, kategorie), subskrypcje
(free vs paid, wygasanie, aktywacja przez event Stripe) oraz no-op notify.

## Uwagi prawne

Scraping rob zgodnie z regulaminem i robots.txt danego serwisu oraz z rozsadnym
rate limitem. Zrodlo Slickdeals sluzy jako publiczny, bezkluczowy przyklad
techniczny.

---

by [FluxLab](https://fluxlab.pl) automatyzacja procesow i wdrozenia AI dla firm.
