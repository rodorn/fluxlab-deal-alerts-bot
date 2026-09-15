"""Warstwa subskrypcji.

- Model uzytkownika (email, tier free/paid, expires_at) w SQLite.
- Sprawdzanie dostepu: paid + niewygasla subskrypcja.
- PLACEHOLDER integracji Stripe: handle_stripe_event() obsluguje mockowany
  event checkout.session.completed i aktywuje subskrypcje. Dziala BEZ klucza
  Stripe (na sam slownik eventu). Realny endpoint webhooka to cienka warstwa
  nad ta funkcja (patrz README, sekcja Stripe).
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

DEFAULT_DB = Path("data/subscriptions.db")


class Tier(str, Enum):
    FREE = "free"
    PAID = "paid"


@dataclass
class User:
    email: str
    tier: Tier
    expires_at: datetime | None

    def is_paid_active(self, now: datetime | None = None) -> bool:
        now = now or datetime.now(timezone.utc)
        if self.tier != Tier.PAID:
            return False
        if self.expires_at is None:
            return False
        return self.expires_at > now


class SubscriptionStore:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                tier TEXT NOT NULL DEFAULT 'free',
                expires_at TEXT
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def upsert_user(
        self,
        email: str,
        tier: Tier = Tier.FREE,
        expires_at: datetime | None = None,
    ) -> User:
        email = email.strip().lower()
        exp = expires_at.isoformat() if expires_at else None
        self.conn.execute(
            """
            INSERT INTO users (email, tier, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                tier=excluded.tier,
                expires_at=excluded.expires_at
            """,
            (email, tier.value, exp),
        )
        self.conn.commit()
        return self.get_user(email)  # type: ignore[return-value]

    def get_user(self, email: str) -> User | None:
        email = email.strip().lower()
        row = self.conn.execute(
            "SELECT email, tier, expires_at FROM users WHERE email=?",
            (email,),
        ).fetchone()
        if not row:
            return None
        exp = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
        return User(email=row["email"], tier=Tier(row["tier"]), expires_at=exp)

    def has_access(self, email: str, now: datetime | None = None) -> bool:
        """Dostep do paid feedu (natychmiastowe alerty)."""
        user = self.get_user(email)
        if not user:
            return False
        return user.is_paid_active(now=now)

    def activate_subscription(self, email: str, days: int = 30) -> User:
        """Aktywuje/przedluza subskrypcje paid. Jesli aktywna, przedluza od
        obecnego expires_at, inaczej od teraz."""
        now = datetime.now(timezone.utc)
        user = self.get_user(email)
        base = now
        if user and user.expires_at and user.expires_at > now:
            base = user.expires_at
        new_exp = base + timedelta(days=days)
        return self.upsert_user(email, tier=Tier.PAID, expires_at=new_exp)


# --- PLACEHOLDER integracji Stripe (dziala na mocku, bez klucza) ---


class StripeWebhookError(ValueError):
    pass


def handle_stripe_event(
    event: dict,
    store: SubscriptionStore,
    days_per_payment: int = 30,
) -> User | None:
    """Obsluguje event Stripe (mock). Na produkcji event pochodzi z
    stripe.Webhook.construct_event(payload, sig, endpoint_secret) w endpoincie
    HTTP; tutaj przyjmujemy juz zdeserializowany slownik, wiec caly przeplyw
    aktywacji da sie testowac bez sekretow.

    Obslugiwany typ: checkout.session.completed -> aktywacja paid dla emaila
    z customer_details.email lub customer_email.
    """
    etype = event.get("type")
    if etype != "checkout.session.completed":
        return None  # ignorujemy inne typy

    obj = event.get("data", {}).get("object", {})
    email = obj.get("customer_email") or obj.get("customer_details", {}).get("email")
    if not email:
        raise StripeWebhookError("brak emaila w evencie checkout.session")

    return store.activate_subscription(email, days=days_per_payment)
