"""Sensor platform for Shopping Promotions PL."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FRONTEND_CARD_TYPE, INTEGRATION_VERSION, STORE_NAMES
from .coordinator import ShoppingPromotionsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up promotion summary sensor."""
    coordinator: ShoppingPromotionsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ShoppingPromotionsSensor(coordinator)])


class ShoppingPromotionsSensor(
    CoordinatorEntity[ShoppingPromotionsCoordinator], SensorEntity
):
    """Number of shopping-list positions with at least one promotion."""

    _attr_has_entity_name = True
    _attr_name = "Produkty na promocji"
    _attr_icon = "mdi:sale"

    def __init__(self, coordinator: ShoppingPromotionsCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_matched_count"

    @property
    def native_value(self) -> int:
        items = (self.coordinator.data or {}).get("items", [])
        return sum(1 for item in items if item.get("matches"))

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        items = data.get("items", [])
        return {
            "total_items": len(items),
            "offers_count": data.get("offers_count", 0),
            "source_entity_id": data.get("source_entity_id"),
            "stores": data.get("stores", []),
            "store_names": STORE_NAMES,
            "items": items,
            "integration_version": INTEGRATION_VERSION,
            "recommended_card": FRONTEND_CARD_TYPE,
        }
