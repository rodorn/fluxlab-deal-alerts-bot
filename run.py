#!/usr/bin/env python3
"""Spina caly przeplyw: scrape (lub demo) -> scoring -> filtr DEAL -> notify wg tieru.

Uzycie:
    python run.py                # zrodlo live (Slickdeals) z fallbackiem demo
    python run.py --source demo  # wymuszony tryb demo (offline)
    python run.py --min-discount 0.25

Powiadomienia sa domyslnie w trybie dry_run (bez realnego POST). Ustaw
DISCORD_WEBHOOK_URL albo TELEGRAM_BOT_TOKEN+TELEGRAM_CHAT_ID i dodaj --send,
aby faktycznie wysylac.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from src.notify import FREE_DELAY_SECONDS_DEFAULT, notify
from src.scoring import deals_only, score_offers
from src.source import get_source
from src.subscription import SubscriptionStore, Tier


def human_delay(seconds: int) -> str:
    if seconds <= 0:
        return "natychmiast"
    h = seconds / 3600
    return f"opoznienie ~{h:.0f}h"


def main() -> int:
    ap = argparse.ArgumentParser(description="deal-alerts-bot (FluxLab)")
    ap.add_argument("--source", default="slickdeals", help="slickdeals|demo")
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--min-discount", type=float, default=0.20)
    ap.add_argument(
        "--free-delay",
        type=int,
        default=FREE_DELAY_SECONDS_DEFAULT,
        help="opoznienie alertow free tier (sekundy)",
    )
    ap.add_argument(
        "--send",
        action="store_true",
        help="faktycznie wysylaj (domyslnie dry_run)",
    )
    args = ap.parse_args()

    print(f"[1/4] Pobieram oferty ze zrodla: {args.source}")
    source = get_source(args.source)
    offers = source.fetch(limit=args.limit)
    used = source.name
    print(f"      pobrano {len(offers)} ofert (zrodlo aktywne: {used})")

    print(f"[2/4] Scoring (min_discount={args.min_discount:.0%})")
    scored = score_offers(offers, min_discount=args.min_discount)
    deals = deals_only(scored)
    print(f"      wykryto {len(deals)} okazji (DEAL) z {len(scored)} ofert")

    # Demo warstwy subskrypcji: uzytkownik free vs paid (baza w pamieci)
    store = SubscriptionStore(":memory:")
    store.upsert_user("free@example.com", tier=Tier.FREE)
    store.activate_subscription("paid@example.com", days=30)
    users = ["free@example.com", "paid@example.com"]

    print("[3/4] Dostep uzytkownikow:")
    for u in users:
        acc = store.has_access(u)
        print(f"      {u}: {'PAID (natychmiast)' if acc else 'FREE (opoznione)'}")

    print(f"[4/4] Alerty (dry_run={not args.send}):")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for s in deals[:10]:
        for u in users:
            is_paid = store.has_access(u)
            res = notify(
                s,
                is_paid=is_paid,
                free_delay_seconds=args.free_delay,
                dry_run=not args.send,
            )
            price = (
                f"{s.offer.price:.2f} {s.offer.currency}"
                if s.offer.price is not None
                else "b/d"
            )
            print(
                f"      -> {u:18s} kanal={res.channel:8s} "
                f"{human_delay(res.delay_seconds):16s} | "
                f"[{s.offer.category}] {s.offer.title[:60]} ({price})"
            )
    if not deals:
        print("      brak okazji do wyslania w tej partii")

    store.close()
    print(f"\nGotowe. {now}. FluxLab https://fluxlab.pl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
