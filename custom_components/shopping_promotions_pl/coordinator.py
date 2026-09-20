"""Coordinator for Shopping Promotions PL."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.components.todo.const import DATA_COMPONENT
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_MATCH_THRESHOLD,
    CONF_MAX_LEAFLETS,
    CONF_SOURCE_TODO,
    CONF_STORES,
    CONF_UPDATE_INTERVAL,
    DEFAULT_MATCH_THRESHOLD,
    DEFAULT_MAX_LEAFLETS,
    DEFAULT_SOURCE_TODO,
    DEFAULT_STORES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .matcher import match_offers
from .models import EnrichedItem
from .providers.blix import BlixError, BlixProvider

_LOGGER = logging.getLogger(__name__)


class ShoppingPromotionsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch promotions and match them to a Home Assistant to-do list."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        settings = dict(entry.data)
        settings.update(entry.options)

        self.source_entity_id = settings.get(CONF_SOURCE_TODO, DEFAULT_SOURCE_TODO)
        self.stores = list(settings.get(CONF_STORES, DEFAULT_STORES))
        self.match_threshold = float(
            settings.get(CONF_MATCH_THRESHOLD, DEFAULT_MATCH_THRESHOLD)
        )
        interval = int(settings.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        max_leaflets = int(settings.get(CONF_MAX_LEAFLETS, DEFAULT_MAX_LEAFLETS))

        self.provider = BlixProvider(
            async_get_clientsession(hass),
            stores=self.stores,
            max_leaflets=max_leaflets,
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=interval),
        )

    def _source_items(self) -> list[Any]:
        component = self.hass.data.get(DATA_COMPONENT)
        if component is None:
            raise UpdateFailed("Home Assistant todo component is not loaded")
        entity = component.get_entity(self.source_entity_id)
        if entity is None:
            raise UpdateFailed(f"To-do entity not found: {self.source_entity_id}")
        return list(entity.todo_items or [])

    async def _async_update_data(self) -> dict[str, Any]:
        source_items = self._source_items()
        try:
            offers = await self.provider.async_get_offers()
        except BlixError as err:
            raise UpdateFailed(f"Blix retrieval failed: {err}") from err

        enriched: list[EnrichedItem] = []
        for item in source_items:
            summary = item.summary or ""
            uid = item.uid or summary
            status_value = getattr(item.status, "value", str(item.status))
            matches = match_offers(
                summary,
                offers,
                threshold=self.match_threshold,
                max_per_store=1,
            )
            enriched.append(
                EnrichedItem(
                    uid=uid,
                    summary=summary,
                    status=status_value,
                    matches=matches,
                )
            )

        return {
            "items": [item.as_dict() for item in enriched],
            "offers_count": len(offers),
            "stores": self.stores,
            "source_entity_id": self.source_entity_id,
        }

    async def async_force_refresh(self) -> None:
        """Clear upstream cache and request a complete refresh."""
        self.provider.clear_cache()
        await self.async_request_refresh()

    def clear_cache(self) -> None:
        """Clear provider cache."""
        self.provider.clear_cache()
