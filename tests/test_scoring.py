from datetime import datetime, timezone

from src.scoring import deals_only, score_offers
from src.source import Offer


def _offer(title, price, category="lego"):
    return Offer(
        title=title,
        price=price,
        currency="USD",
        url="https://example.com/" + title.replace(" ", "-"),
        image=None,
        category=category,
        seen_at=datetime.now(timezone.utc),
    )


def test_deal_flag_below_median():
    offers = [
        _offer("A", 100),
        _offer("B", 100),
        _offer("C", 60),  # 40% ponizej mediany 100 -> DEAL
    ]
    scored = score_offers(offers, min_discount=0.20)
    by_title = {s.offer.title: s for s in scored}
    assert by_title["C"].is_deal is True
    assert by_title["A"].is_deal is False
    assert abs(by_title["C"].discount_pct - 0.40) < 1e-9


def test_no_deal_when_above_threshold():
    offers = [_offer("A", 100), _offer("B", 100), _offer("C", 95)]
    scored = score_offers(offers, min_discount=0.20)
    assert deals_only(scored) == []


def test_absolute_threshold_triggers_deal():
    offers = [_offer("A", 100), _offer("B", 100), _offer("C", 90)]
    # 10% ponizej mediany to za malo, ale absolutny prog 95 zapali DEAL
    scored = score_offers(offers, min_discount=0.20, abs_threshold={"lego": 95.0})
    by_title = {s.offer.title: s for s in scored}
    assert by_title["C"].is_deal is True


def test_missing_price_is_not_deal():
    offers = [_offer("A", 100), _offer("B", 100), _offer("C", None)]
    scored = score_offers(offers)
    by_title = {s.offer.title: s for s in scored}
    assert by_title["C"].is_deal is False
    assert by_title["C"].reason == "brak ceny"


def test_categories_scored_independently():
    offers = [
        _offer("L1", 100, "lego"),
        _offer("L2", 100, "lego"),
        _offer("S1", 200, "sneakers"),
        _offer("S2", 200, "sneakers"),
        _offer("S3", 100, "sneakers"),  # 50% ponizej mediany sneakers
    ]
    scored = score_offers(offers, min_discount=0.20)
    by_title = {s.offer.title: s for s in scored}
    assert by_title["S3"].is_deal is True
    assert by_title["L1"].is_deal is False
