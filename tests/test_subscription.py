from datetime import datetime, timedelta, timezone

import pytest

from src.subscription import (
    StripeWebhookError,
    SubscriptionStore,
    Tier,
    handle_stripe_event,
)


@pytest.fixture
def store():
    s = SubscriptionStore(":memory:")
    yield s
    s.close()


def test_free_user_has_no_access(store):
    store.upsert_user("free@example.com", tier=Tier.FREE)
    assert store.has_access("free@example.com") is False


def test_paid_user_has_access(store):
    store.activate_subscription("paid@example.com", days=30)
    assert store.has_access("paid@example.com") is True


def test_unknown_user_no_access(store):
    assert store.has_access("nobody@example.com") is False


def test_expired_subscription_no_access(store):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    store.upsert_user("old@example.com", tier=Tier.PAID, expires_at=past)
    assert store.has_access("old@example.com") is False


def test_activation_extends_from_existing_expiry(store):
    store.activate_subscription("p@example.com", days=30)
    u1 = store.get_user("p@example.com")
    store.activate_subscription("p@example.com", days=30)
    u2 = store.get_user("p@example.com")
    # przedluzenie sumuje sie (okolo 60 dni od teraz)
    assert u2.expires_at > u1.expires_at
    delta = u2.expires_at - datetime.now(timezone.utc)
    assert timedelta(days=59) < delta < timedelta(days=61)


def test_email_normalized(store):
    store.activate_subscription("MixedCase@Example.com", days=30)
    assert store.has_access("mixedcase@example.com") is True


def test_stripe_event_activates(store):
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer_email": "buyer@example.com"}},
    }
    user = handle_stripe_event(event, store, days_per_payment=30)
    assert user is not None
    assert user.tier == Tier.PAID
    assert store.has_access("buyer@example.com") is True


def test_stripe_event_customer_details_email(store):
    event = {
        "type": "checkout.session.completed",
        "data": {"object": {"customer_details": {"email": "b2@example.com"}}},
    }
    handle_stripe_event(event, store)
    assert store.has_access("b2@example.com") is True


def test_stripe_other_event_ignored(store):
    event = {"type": "payment_intent.created", "data": {"object": {}}}
    assert handle_stripe_event(event, store) is None


def test_stripe_event_missing_email_raises(store):
    event = {"type": "checkout.session.completed", "data": {"object": {}}}
    with pytest.raises(StripeWebhookError):
        handle_stripe_event(event, store)
