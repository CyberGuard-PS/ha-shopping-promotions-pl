"""Shopping Promotions PL integration."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_CACHE,
    SERVICE_REFRESH,
)
from .coordinator import ShoppingPromotionsCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level services."""
    hass.data.setdefault(DOMAIN, {})

    async def _refresh(_: ServiceCall) -> None:
        coordinators = list(hass.data.get(DOMAIN, {}).values())
        await asyncio.gather(
            *(
                coordinator.async_force_refresh()
                for coordinator in coordinators
                if isinstance(coordinator, ShoppingPromotionsCoordinator)
            ),
            return_exceptions=True,
        )

    @callback
    def _clear_cache(_: ServiceCall) -> None:
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(coordinator, ShoppingPromotionsCoordinator):
                coordinator.clear_cache()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _refresh)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_CACHE, _clear_cache)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    coordinator = ShoppingPromotionsCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    @callback
    def _schedule_refresh(*_: object) -> None:
        hass.async_create_task(coordinator.async_request_refresh())

    # Generic to-do entities expose their count as state, so additions,
    # completions and removals cause a state change.
    unsub_state = async_track_state_change_event(
        hass, [coordinator.source_entity_id], _schedule_refresh
    )

    # Native Shopping List emits this event also for rename/reorder changes.
    @callback
    def _shopping_list_event(event) -> None:
        _schedule_refresh()

    unsub_shopping = hass.bus.async_listen(
        "shopping_list_updated", _shopping_list_event
    )

    entry.async_on_unload(unsub_state)
    entry.async_on_unload(unsub_shopping)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded
