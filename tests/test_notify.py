from datetime import datetime, timezone

from src.notify import (
    FREE_DELAY_SECONDS_DEFAULT,
    delay_for_tier,
    format_message,
    notify,
)
from src.scoring import ScoredOffer
from src.source import Offer


def _scored():
    o = Offer(
        title="LEGO Icons 10307 Eiffel Tower",
        price=479.99,
        currency="USD",
        url="https://example.com/lego",
        image=None,
        category="lego",
        seen_at=datetime.now(timezone.utc),
    )
    return ScoredOffer(
        o, median=629.99, discount_pct=0.24, is_deal=True, reason="24% ponizej mediany"
    )


def test_notify_noop_without_channel():
    res = notify(_scored(), is_paid=True, env={})
    assert res.sent is False
    assert res.channel == "noop"


def test_paid_immediate_delay():
    assert delay_for_tier(True, FREE_DELAY_SECONDS_DEFAULT) == 0


def test_free_delayed():
    assert (
        delay_for_tier(False, FREE_DELAY_SECONDS_DEFAULT) == FREE_DELAY_SECONDS_DEFAULT
    )


def test_dry_run_discord_reports_sent():
    env = {"DISCORD_WEBHOOK_URL": "https://discord.example/webhook"}
    res = notify(_scored(), is_paid=True, dry_run=True, env=env)
    assert res.sent is True
    assert res.channel == "discord"
    assert res.delay_seconds == 0


def test_dry_run_telegram_free_delay():
    env = {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": "123"}
    res = notify(_scored(), is_paid=False, dry_run=True, env=env)
    assert res.channel == "telegram"
    assert res.delay_seconds == FREE_DELAY_SECONDS_DEFAULT


def test_format_message_contains_key_fields():
    msg = format_message(_scored())
    assert "DEAL" in msg
    assert "lego" in msg
    assert "479.99 USD" in msg
    assert "https://example.com/lego" in msg
