"""Zrodla ofert.

Definiuje abstrakcyjny interfejs zrodla (DealSource) oraz dwie implementacje:
- SlickdealsSource: dzialajace, bezkluczowe zrodlo (publiczny RSS Slickdeals),
- DemoSource: wbudowany przyklad, uzywany takze jako fallback gdy zrodlo zawodzi.

Model oferty (Offer) jest kategorio-agnostyczny: dowolny marketplace mozna
podpiac implementujac klase DealSource.fetch().
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    import requests
except ImportError:  # requests jest opcjonalny dla trybu demo
    requests = None  # type: ignore

DEFAULT_UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"

# regex na kwote w tytule/opisie, np. "$11.25", "$1,299.99"
_PRICE_RE = re.compile(r"\$\s?([0-9][0-9,]*\.?[0-9]{0,2})")
_IMG_RE = re.compile(r'<img[^>]+src="([^"]+)"', re.IGNORECASE)

# proste mapowanie slow kluczowych na kategorie (kategorio-agnostyczne rozszerzalne)
_CATEGORY_KEYWORDS = {
    "lego": "lego",
    "sneaker": "sneakers",
    "nike": "sneakers",
    "adidas": "sneakers",
    "jordan": "sneakers",
    "gpu": "electronics",
    "rtx": "electronics",
    "ssd": "electronics",
    "laptop": "electronics",
    "monitor": "electronics",
    "tv": "electronics",
    "battery": "home",
    "batteries": "home",
}


@dataclass
class Offer:
    """Pojedyncza oferta z marketplace."""

    title: str
    price: float | None
    currency: str
    url: str
    image: str | None = None
    category: str = "general"
    seen_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["seen_at"] = self.seen_at.isoformat()
        return d


def guess_category(title: str) -> str:
    low = title.lower()
    for kw, cat in _CATEGORY_KEYWORDS.items():
        if kw in low:
            return cat
    return "general"


def parse_price(text: str) -> float | None:
    m = _PRICE_RE.search(text or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


class DealSource(ABC):
    """Abstrakcyjny interfejs zrodla ofert."""

    name: str = "abstract"

    @abstractmethod
    def fetch(self, limit: int = 50) -> list[Offer]:
        """Zwraca liste ofert. Implementacja nie moze rzucac wyjatku sieci na zewnatrz
        jesli udostepnia fallback; inaczej wywolujacy sam decyduje o obsludze bledu."""
        raise NotImplementedError


class DemoSource(DealSource):
    """Wbudowany przyklad. Dziala offline, sluzy tez jako fallback."""

    name = "demo"

    _SAMPLE = [
        {
            "title": "LEGO Icons 10307 Eiffel Tower $479.99 (was $629.99)",
            "price": 479.99,
            "url": "https://example.com/lego-10307",
            "image": "https://example.com/img/10307.jpg",
            "category": "lego",
        },
        {
            "title": "LEGO Star Wars 75192 Millennium Falcon $699.99",
            "price": 699.99,
            "url": "https://example.com/lego-75192",
            "image": "https://example.com/img/75192.jpg",
            "category": "lego",
        },
        {
            "title": "LEGO Icons 10307 Eiffel Tower $629.99 (retail)",
            "price": 629.99,
            "url": "https://example.com/lego-10307-retail",
            "image": None,
            "category": "lego",
        },
        {
            "title": "Nike Air Jordan 1 Retro High OG $109.99 (was $180)",
            "price": 109.99,
            "url": "https://example.com/aj1",
            "image": "https://example.com/img/aj1.jpg",
            "category": "sneakers",
        },
        {
            "title": "Nike Air Jordan 1 Retro High OG $170.00",
            "price": 170.00,
            "url": "https://example.com/aj1-b",
            "image": None,
            "category": "sneakers",
        },
        {
            "title": "Adidas Samba OG $89.99",
            "price": 89.99,
            "url": "https://example.com/samba",
            "image": None,
            "category": "sneakers",
        },
    ]

    def fetch(self, limit: int = 50) -> list[Offer]:
        offers = []
        for row in self._SAMPLE[:limit]:
            offers.append(
                Offer(
                    title=row["title"],
                    price=row["price"],
                    currency="USD",
                    url=row["url"],
                    image=row["image"],
                    category=row["category"],
                )
            )
        return offers


class SlickdealsSource(DealSource):
    """Dzialajace, bezkluczowe zrodlo: publiczny RSS frontpage Slickdeals.

    Nie wymaga logowania ani klucza API. Ceny sa parsowane z tytulu/opisu,
    obrazek z content:encoded, kategoria zgadywana ze slow kluczowych.
    Przy bledzie sieci/parsowania zwraca dane z DemoSource (jesli fallback=True).
    """

    name = "slickdeals"
    URL = (
        "https://slickdeals.net/newsearch.php"
        "?mode=frontpage&searcharea=deals&searchin=first&rss=1"
    )
    _CONTENT_NS = "{http://purl.org/rss/1.0/modules/content/}encoded"

    def __init__(self, fallback: bool = True, timeout: int = 15):
        self.fallback = fallback
        self.timeout = timeout

    def _fetch_raw(self) -> str:
        if requests is None:
            raise RuntimeError("requests niedostepny")
        resp = requests.get(
            self.URL, headers={"User-Agent": DEFAULT_UA}, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.text

    def parse(self, xml_text: str, limit: int = 50) -> list[Offer]:
        root = ET.fromstring(xml_text)
        offers: list[Offer] = []
        for item in root.iterfind(".//item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            desc = item.findtext("description") or ""
            content = item.findtext(self._CONTENT_NS) or ""
            price = parse_price(title) or parse_price(desc)
            img_m = _IMG_RE.search(content)
            image = img_m.group(1) if img_m else None
            if not title or not link:
                continue
            offers.append(
                Offer(
                    title=title,
                    price=price,
                    currency="USD",
                    url=link,
                    image=image,
                    category=guess_category(title),
                )
            )
            if len(offers) >= limit:
                break
        return offers

    def fetch(self, limit: int = 50) -> list[Offer]:
        try:
            xml_text = self._fetch_raw()
            offers = self.parse(xml_text, limit=limit)
            if not offers:
                raise ValueError("pusty feed")
            return offers
        except Exception:
            if self.fallback:
                return DemoSource().fetch(limit=limit)
            raise


def get_source(name: str = "slickdeals", **kwargs) -> DealSource:
    """Fabryka zrodel."""
    name = (name or "").lower()
    if name in ("slickdeals", "live", "auto"):
        return SlickdealsSource(**kwargs)
    if name == "demo":
        return DemoSource()
    raise ValueError(f"nieznane zrodlo: {name}")
