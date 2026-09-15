"""Powiadomienia o okazjach (Discord / Telegram).

- Kanaly konfigurowane przez env: DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID.
- Bez skonfigurowanego kanalu funkcja jest no-op (zwraca NotifyResult(sent=False, channel="noop")).
- Tier steruje opoznieniem: free = opoznienie free_delay_seconds (domyslnie 6-12h),
  paid = natychmiast (0 s). W trybie demo opoznienie jest raportowane, nie odczekiwane.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from .scoring import ScoredOffer

# free tier: alert opozniony o 6-12h (sekundy). Wartosc domyslna = srodek zakresu.
FREE_DELAY_SECONDS_DEFAULT = 9 * 3600
FREE_DELAY_RANGE = (6 * 3600, 12 * 3600)


@dataclass
class NotifyResult:
    sent: bool
    channel: str
    delay_seconds: int
    detail: str = ""


def format_message(scored: ScoredOffer) -> str:
    o = scored.offer
    price = f"{o.price:.2f} {o.currency}" if o.price is not None else "b/d"
    lines = [
        f"DEAL [{o.category}] {o.title}",
        f"Cena: {price} | {scored.reason}",
        o.url,
    ]
    return "\n".join(lines)


def delay_for_tier(is_paid: bool, free_delay_seconds: int) -> int:
    return 0 if is_paid else free_delay_seconds


def _send_discord(text: str, url: str, timeout: int = 10) -> bool:
    if requests is None:
        return False
    resp = requests.post(url, json={"content": text}, timeout=timeout)
    return 200 <= resp.status_code < 300


def _send_telegram(text: str, token: str, chat_id: str, timeout: int = 10) -> bool:
    if requests is None:
        return False
    api = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        api,
        json={"chat_id": chat_id, "text": text, "disable_web_page_preview": False},
        timeout=timeout,
    )
    return 200 <= resp.status_code < 300


def notify(
    scored: ScoredOffer,
    is_paid: bool,
    free_delay_seconds: int = FREE_DELAY_SECONDS_DEFAULT,
    dry_run: bool = False,
    env: dict | None = None,
) -> NotifyResult:
    """Wysyla alert wg tieru. Zwraca NotifyResult opisujacy kanal i opoznienie.

    - dry_run=True: nie wykonuje realnego POST (uzyteczne w demo/testach).
    - Brak env kanalu: no-op.
    """
    env = env if env is not None else dict(os.environ)
    text = format_message(scored)
    delay = delay_for_tier(is_paid, free_delay_seconds)

    discord_url = env.get("DISCORD_WEBHOOK_URL")
    tg_token = env.get("TELEGRAM_BOT_TOKEN")
    tg_chat = env.get("TELEGRAM_CHAT_ID")

    if discord_url:
        if dry_run:
            return NotifyResult(True, "discord", delay, "dry_run")
        ok = _send_discord(text, discord_url)
        return NotifyResult(ok, "discord", delay, "" if ok else "blad POST")

    if tg_token and tg_chat:
        if dry_run:
            return NotifyResult(True, "telegram", delay, "dry_run")
        ok = _send_telegram(text, tg_token, tg_chat)
        return NotifyResult(ok, "telegram", delay, "" if ok else "blad POST")

    return NotifyResult(False, "noop", delay, "brak skonfigurowanego kanalu")
