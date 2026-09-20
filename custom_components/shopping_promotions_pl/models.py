"""Data models for Shopping Promotions PL."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class Offer:
    """Normalized promotional offer."""

    store: str
    name: str
    promo_price: float | None = None
    regular_price: float | None = None
    regular_price_estimated: bool = False
    discount_percent: float | None = None
    brand: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    leaflet_id: str | None = None
    page: int | None = None
    source: str = "blix"
    match_score: float | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serialize offer."""
        return asdict(self)


@dataclass(slots=True)
class EnrichedItem:
    """Shopping-list item with promotion matches."""

    uid: str
    summary: str
    status: str
    matches: list[Offer]

    def as_dict(self) -> dict[str, Any]:
        """Serialize enriched item."""
        return {
            "uid": self.uid,
            "summary": self.summary,
            "status": self.status,
            "matches": [match.as_dict() for match in self.matches],
        }
