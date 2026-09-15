"""Ocena okazji (scoring).

Model: dla kazdej kategorii liczymy mediane ceny w biezacej partii ofert.
Oferta dostaje wynik na podstawie odchylenia od mediany (im tansza wzgledem
mediany, tym wyzszy discount_pct). Flaga DEAL zapala sie gdy:
- discount_pct >= min_discount (domyslnie 0.20 = 20% ponizej mediany), lub
- cena spadnie ponizej absolutnego progu (opcjonalny abs_threshold per kategoria).

Kategorio-agnostyczne: nie zaklada zadnej konkretnej kategorii.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .source import Offer


@dataclass
class ScoredOffer:
    offer: Offer
    median: float | None
    discount_pct: float | None  # 0.25 == 25% ponizej mediany kategorii
    is_deal: bool
    reason: str


def _medians_by_category(offers: list[Offer]) -> dict[str, float]:
    buckets: dict[str, list[float]] = {}
    for o in offers:
        if o.price is None:
            continue
        buckets.setdefault(o.category, []).append(o.price)
    return {cat: statistics.median(prices) for cat, prices in buckets.items() if prices}


def score_offers(
    offers: list[Offer],
    min_discount: float = 0.20,
    abs_threshold: dict[str, float] | None = None,
) -> list[ScoredOffer]:
    """Ocenia liste ofert i zwraca ScoredOffer dla kazdej."""
    abs_threshold = abs_threshold or {}
    medians = _medians_by_category(offers)
    result: list[ScoredOffer] = []

    for o in offers:
        median = medians.get(o.category)
        discount_pct: float | None = None
        is_deal = False
        reasons: list[str] = []

        if o.price is None:
            result.append(ScoredOffer(o, median, None, False, "brak ceny"))
            continue

        if median and median > 0:
            discount_pct = (median - o.price) / median
            if discount_pct >= min_discount:
                is_deal = True
                reasons.append(
                    f"{discount_pct * 100:.0f}% ponizej mediany "
                    f"({median:.2f} {o.currency})"
                )

        thr = abs_threshold.get(o.category)
        if thr is not None and o.price <= thr:
            is_deal = True
            reasons.append(f"cena <= prog {thr:.2f} {o.currency}")

        reason = "; ".join(reasons) if reasons else "brak sygnalu DEAL"
        result.append(ScoredOffer(o, median, discount_pct, is_deal, reason))

    return result


def deals_only(scored: list[ScoredOffer]) -> list[ScoredOffer]:
    return [s for s in scored if s.is_deal]
