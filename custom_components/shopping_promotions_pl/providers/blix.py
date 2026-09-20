"""Blix promotional-leaflet provider.

Blix currently embeds a structured window.offers JSON array in leaflet pages.
This adapter intentionally performs low-frequency, read-only HTTP retrieval
and keeps a TTL cache to avoid unnecessary load.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
import html as html_lib
import json
import logging
import re
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

from ..models import Offer

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://blix.pl"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)
LEAFLET_LINK_RE_TEMPLATE = r"/sklep/{slug}/gazetka/(\d+)/?"
TAG_RE = re.compile(r"<[^>]+>")
DATE_RANGE_RE = re.compile(
    r"Termin\s+obowiązywania:\s*(\d{1,2})[./-](\d{1,2})\s*[-–]\s*"
    r"(\d{1,2})[./-](\d{1,2})",
    re.IGNORECASE,
)


class BlixError(Exception):
    """Blix retrieval/parsing error."""


class BlixProvider:
    """Fetch and normalize current Blix offers."""

    def __init__(
        self,
        session: ClientSession,
        stores: list[str],
        max_leaflets: int = 8,
        cache_ttl: timedelta = timedelta(hours=3),
    ) -> None:
        self._session = session
        self._stores = stores
        self._max_leaflets = max_leaflets
        self._cache_ttl = cache_ttl
        self._cache: list[Offer] | None = None
        self._cache_time: datetime | None = None

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache = None
        self._cache_time = None

    async def async_get_offers(self, force: bool = False) -> list[Offer]:
        """Return normalized offers across configured stores."""
        now = datetime.now()
        if (
            not force
            and self._cache is not None
            and self._cache_time is not None
            and now - self._cache_time < self._cache_ttl
        ):
            return list(self._cache)

        tasks = [self._fetch_store(store) for store in self._stores]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        offers: list[Offer] = []
        failures: list[str] = []
        for store, result in zip(self._stores, results, strict=True):
            if isinstance(result, Exception):
                failures.append(f"{store}: {result}")
                _LOGGER.warning("Blix source failed for %s: %s", store, result)
                continue
            offers.extend(result)

        if not offers and failures:
            raise BlixError("; ".join(failures))

        # Keep only offers valid today when Blix exposes validity dates.
        offers = [offer for offer in offers if _is_current_offer(offer)]

        # De-duplicate the same product repeated on a leaflet or page.
        unique: dict[tuple[Any, ...], Offer] = {}
        for offer in offers:
            key = (
                offer.store,
                offer.name.casefold(),
                offer.promo_price,
                offer.valid_from,
                offer.valid_to,
            )
            unique[key] = offer

        self._cache = list(unique.values())
        self._cache_time = now
        return list(self._cache)

    async def _fetch_store(self, store: str) -> list[Offer]:
        store_url = f"{BASE_URL}/sklep/{store}/"
        body = await self._get_text(store_url)
        pattern = re.compile(LEAFLET_LINK_RE_TEMPLATE.format(slug=re.escape(store)))
        leaflet_ids = list(dict.fromkeys(pattern.findall(body)))[: self._max_leaflets]

        if not leaflet_ids:
            raise BlixError(f"no leaflet IDs found at {store_url}")

        output: list[Offer] = []
        # Sequential within one store: gentler for the upstream service.
        for leaflet_id in leaflet_ids:
            url = f"{BASE_URL}/sklep/{store}/gazetka/{leaflet_id}/"
            try:
                leaflet_html = await self._get_text(url)
                output.extend(
                    self._parse_leaflet(
                        store=store,
                        leaflet_id=leaflet_id,
                        source_url=url,
                        raw_html=leaflet_html,
                    )
                )
                await asyncio.sleep(0.20)
            except BlixError as err:
                _LOGGER.debug("Skipping Blix leaflet %s: %s", url, err)
        return output

    async def _get_text(self, url: str) -> str:
        try:
            async with self._session.get(
                url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.6",
                },
                timeout=ClientTimeout(total=25),
                allow_redirects=True,
            ) as response:
                if response.status >= 400:
                    raise BlixError(f"HTTP {response.status}")
                return await response.text(errors="replace")
        except (ClientError, TimeoutError) as err:
            raise BlixError(str(err)) from err

    def _parse_leaflet(
        self,
        store: str,
        leaflet_id: str,
        source_url: str,
        raw_html: str,
    ) -> list[Offer]:
        raw_offers = _extract_window_offers(raw_html)
        if not isinstance(raw_offers, list):
            raise BlixError("window.offers was not an array")

        valid_from, valid_to = _leaflet_dates(raw_html)
        output: list[Offer] = []
        for raw in raw_offers:
            if not isinstance(raw, dict):
                continue
            offer = _normalize_offer(
                raw,
                store=store,
                leaflet_id=leaflet_id,
                source_url=source_url,
                fallback_from=valid_from,
                fallback_to=valid_to,
            )
            if offer is not None:
                output.append(offer)
        return output


def _is_current_offer(offer: Offer) -> bool:
    """Return True if an offer is current or its dates are unknown."""
    today = date.today()
    try:
        if offer.valid_from and date.fromisoformat(offer.valid_from) > today:
            return False
        if offer.valid_to and date.fromisoformat(offer.valid_to) < today:
            return False
    except ValueError:
        # Preserve the record if upstream emitted an unexpected date format.
        return True
    return True


def _extract_window_offers(raw_html: str) -> Any:
    """Extract the balanced JSON array assigned to window.offers."""
    match = re.search(r"window\.offers\s*=\s*", raw_html)
    if not match:
        # Some deployments can omit `window.`.
        match = re.search(r"\boffers\s*=\s*", raw_html)
    if not match:
        raise BlixError("window.offers marker not found")

    start = raw_html.find("[", match.end())
    if start < 0:
        raise BlixError("offer array start not found")

    fragment = _balanced_array(raw_html, start)
    try:
        return json.loads(fragment)
    except json.JSONDecodeError as err:
        # Basic JS-to-JSON compatibility fallback.
        cleaned = re.sub(r",\s*([}\]])", r"\1", fragment)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as nested:
            raise BlixError(f"invalid offer JSON: {nested}") from err


def _balanced_array(text: str, start: int) -> str:
    depth = 0
    quote: str | None = None
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in ("'", '"'):
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise BlixError("unterminated offer array")


def _strip_html(raw_html: str) -> str:
    text = TAG_RE.sub(" ", raw_html)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text)


def _leaflet_dates(raw_html: str) -> tuple[str | None, str | None]:
    text = _strip_html(raw_html)
    match = DATE_RANGE_RE.search(text)
    if not match:
        return None, None

    d1, m1, d2, m2 = (int(value) for value in match.groups())
    today = date.today()
    year1 = today.year
    year2 = year1
    # Handle December -> January promotional ranges.
    if m1 == 12 and m2 == 1:
        year2 += 1

    try:
        start = date(year1, m1, d1)
        end = date(year2, m2, d2)
    except ValueError:
        return None, None

    # If the parsed range is implausibly far in the future, it is likely
    # a page whose year belongs to the previous year.
    if start > today + timedelta(days=180):
        start = start.replace(year=start.year - 1)
        if end.month == 1 and start.month == 12:
            end = end.replace(year=start.year + 1)
        else:
            end = end.replace(year=start.year)

    return start.isoformat(), end.isoformat()


def _dig(data: dict[str, Any], paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = data
        ok = True
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                ok = False
                break
            current = current[part]
        if ok and current not in (None, "", []):
            return current
    return None


def _text(data: dict[str, Any], paths: tuple[str, ...]) -> str | None:
    value = _dig(data, paths)
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("name") or value.get("title") or value.get("value")
    return str(value).strip() if value is not None else None


def _price(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, dict):
        for key in ("value", "amount", "price", "gross"):
            if key in value:
                return _price(value[key])
        return None
    if isinstance(value, int):
        # Blix window.offers uses integer grosze.
        return round(value / 100.0, 2)
    if isinstance(value, float):
        return round(value, 2)

    raw = str(value).lower().replace("\xa0", " ").replace("zł", "").strip()
    raw = raw.replace(" ", "").replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return None
    parsed = float(match.group())
    # Plain integer-looking string values from Blix are normally grosze.
    if "." not in raw and parsed >= 50:
        parsed /= 100.0
    return round(parsed, 2)


def _percent(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("percent", "percentage", "value"):
            if key in value:
                return _percent(value[key])
        return None
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    if not match:
        return None
    result = float(match.group().replace(",", "."))
    if 0 < result < 100:
        return result
    return None


def _date_text(data: dict[str, Any], paths: tuple[str, ...]) -> str | None:
    value = _dig(data, paths)
    if value is None:
        return None
    raw = str(value)
    # Keep ISO-like values compactly.
    iso = re.search(r"\d{4}-\d{2}-\d{2}", raw)
    if iso:
        return iso.group(0)
    dmy = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{4})", raw)
    if dmy:
        d, m, y = map(int, dmy.groups())
        try:
            return date(y, m, d).isoformat()
        except ValueError:
            return None
    return None


def _normalize_offer(
    raw: dict[str, Any],
    *,
    store: str,
    leaflet_id: str,
    source_url: str,
    fallback_from: str | None,
    fallback_to: str | None,
) -> Offer | None:
    name = _text(
        raw,
        (
            "name",
            "title",
            "productName",
            "offerName",
            "product.name",
            "product.title",
        ),
    )
    if not name:
        return None

    promo_price = _price(
        _dig(
            raw,
            (
                "promoPrice",
                "promotionalPrice",
                "salePrice",
                "currentPrice",
                "price",
                "price.value",
                "product.price",
            ),
        )
    )
    regular_price = _price(
        _dig(
            raw,
            (
                "regularPrice",
                "originalPrice",
                "oldPrice",
                "previousPrice",
                "priceBefore",
                "basePrice",
                "product.regularPrice",
            ),
        )
    )
    discount_percent = _percent(
        _dig(
            raw,
            (
                "discountPercent",
                "discountPct",
                "discount.percentage",
                "discount.percent",
            ),
        )
    )

    regular_estimated = False
    if (
        regular_price is None
        and promo_price is not None
        and discount_percent is not None
        and 0 < discount_percent < 90
    ):
        regular_price = round(promo_price / (1 - discount_percent / 100), 2)
        regular_estimated = True

    page_value = _dig(raw, ("page", "pageNumber", "page_number"))
    try:
        page = int(page_value) if page_value is not None else None
    except (TypeError, ValueError):
        page = None

    return Offer(
        store=store,
        name=name,
        brand=_text(raw, ("brandName", "brand", "brand.name", "product.brand")),
        promo_price=promo_price,
        regular_price=regular_price,
        regular_price_estimated=regular_estimated,
        discount_percent=discount_percent,
        valid_from=_date_text(
            raw,
            ("validFrom", "dateFrom", "startDate", "promotionStartDate"),
        )
        or fallback_from,
        valid_to=_date_text(
            raw,
            ("validTo", "validUntil", "dateTo", "endDate", "promotionEndDate"),
        )
        or fallback_to,
        image_url=_text(raw, ("imageUrl", "image", "product.imageUrl", "product.image")),
        source_url=source_url,
        leaflet_id=leaflet_id,
        page=page,
    )
