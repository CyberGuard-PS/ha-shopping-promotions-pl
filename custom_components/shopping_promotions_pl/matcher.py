"""Product-name matching."""
from __future__ import annotations

from difflib import SequenceMatcher
import re
import unicodedata

from .models import Offer

_UNIT_RE = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:kg|g|mg|l|ml|cl|szt|szt\.|opak|op\.|pak|x)\b",
    re.IGNORECASE,
)
_PUNCT_RE = re.compile(r"[^a-z0-9%]+")
_STOPWORDS = {
    "szt", "sztuka", "opak", "opakowanie", "op", "promocja", "kup", "x",
    "duzy", "duza", "duze", "maly", "mala", "male",
}


def normalize(value: str) -> str:
    """Normalize a Polish product name for matching."""
    value = value.casefold().replace("ł", "l")
    value = "".join(
        c for c in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(c)
    )
    value = _UNIT_RE.sub(" ", value)
    value = _PUNCT_RE.sub(" ", value)
    tokens = [token for token in value.split() if token not in _STOPWORDS]
    return " ".join(tokens)


def _tokens(value: str) -> set[str]:
    return {x for x in normalize(value).split() if len(x) > 1}


def score(query: str, candidate: str) -> float:
    """Return a conservative fuzzy-match score in the 0..1 range."""
    qn = normalize(query)
    cn = normalize(candidate)
    if not qn or not cn:
        return 0.0
    if qn == cn:
        return 1.0

    q = _tokens(qn)
    c = _tokens(cn)
    if not q or not c:
        return 0.0

    # A one-word shopping item such as "mleko" should match "Mleko UHT ...".
    containment = len(q & c) / len(q)
    jaccard = len(q & c) / len(q | c)
    sequence = SequenceMatcher(None, qn, cn).ratio()

    # Exact phrase/token containment is more meaningful for grocery names
    # than generic edit distance.
    substring_bonus = 1.0 if qn in cn else 0.0
    return max(
        (0.62 * containment) + (0.20 * jaccard) + (0.18 * sequence),
        0.86 if substring_bonus else 0.0,
    )


def match_offers(
    query: str,
    offers: list[Offer],
    threshold: float,
    max_per_store: int = 1,
) -> list[Offer]:
    """Find the best matching current offer in every store."""
    per_store: dict[str, list[Offer]] = {}
    for offer in offers:
        current_score = score(query, offer.name)
        if current_score < threshold:
            continue
        clone = Offer(**{**offer.as_dict(), "match_score": round(current_score, 3)})
        per_store.setdefault(offer.store, []).append(clone)

    output: list[Offer] = []
    for store_matches in per_store.values():
        store_matches.sort(
            key=lambda item: (
                -(item.match_score or 0.0),
                item.promo_price if item.promo_price is not None else 10**9,
            )
        )
        output.extend(store_matches[:max_per_store])

    output.sort(
        key=lambda item: (
            item.promo_price is None,
            item.promo_price if item.promo_price is not None else 10**9,
            item.store,
        )
    )
    return output
