"""Enriched to-do list platform."""
from __future__ import annotations

from datetime import date
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STORE_NAMES
from .coordinator import ShoppingPromotionsCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up enriched shopping list."""
    coordinator: ShoppingPromotionsCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ShoppingPromotionsTodo(coordinator)])


class ShoppingPromotionsTodo(
    CoordinatorEntity[ShoppingPromotionsCoordinator], TodoListEntity
):
    """Mirror source list and attach promotional details as descriptions."""

    _attr_has_entity_name = True
    _attr_name = "Promocje zakupowe"
    _attr_icon = "mdi:cart-percent"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
    )

    def __init__(self, coordinator: ShoppingPromotionsCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_promotions_todo"

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return enriched items."""
        output: list[TodoItem] = []
        for item in (self.coordinator.data or {}).get("items", []):
            status = (
                TodoItemStatus.COMPLETED
                if item.get("status") == TodoItemStatus.COMPLETED.value
                else TodoItemStatus.NEEDS_ACTION
            )
            output.append(
                TodoItem(
                    uid=item.get("uid"),
                    summary=item.get("summary"),
                    status=status,
                    description=_description(item),
                )
            )
        return output

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create item in the source list."""
        await self.hass.services.async_call(
            "todo",
            "add_item",
            {
                "entity_id": self.coordinator.source_entity_id,
                "item": item.summary,
            },
            blocking=True,
        )
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Propagate supported changes to the source list.

        Description belongs to this derived list and is intentionally ignored.
        """
        current = next(
            (x for x in self.todo_items if x.uid == item.uid),
            None,
        )
        payload: dict[str, Any] = {
            "entity_id": self.coordinator.source_entity_id,
            "item": item.uid,
        }
        if current is None or item.summary != current.summary:
            payload["rename"] = item.summary
        if current is None or item.status != current.status:
            payload["status"] = item.status.value

        if len(payload) > 2:
            await self.hass.services.async_call(
                "todo",
                "update_item",
                payload,
                blocking=True,
            )
            await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete items from the source list."""
        await self.hass.services.async_call(
            "todo",
            "remove_item",
            {
                "entity_id": self.coordinator.source_entity_id,
                "item": uids,
            },
            blocking=True,
        )
        await self.coordinator.async_request_refresh()


def _money(value: float | None) -> str:
    if value is None:
        return "brak danych"
    return f"{value:.2f} zł".replace(".", ",")


def _date_pl(value: str | None) -> str:
    """Format ISO date as dd.mm.yyyy while preserving unknown values."""
    if not value:
        return "brak danych"
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d.%m.%Y")


def _description(item: dict[str, Any]) -> str:
    """Build readable Markdown for the built-in To-do UI.

    Home Assistant's native To-do card may visually clamp long descriptions.
    The bundled Shopping Promotions PL custom card displays all details without
    truncation; this description is intentionally compact and Markdown-friendly.
    """
    matches = item.get("matches", [])
    if not matches:
        return (
            "**Brak aktualnej promocji** w monitorowanych źródłach.  \n"
            "Nie oznacza to, że produktu nie ma w sklepie."
        )

    headline = " • ".join(
        f"**{STORE_NAMES.get(match.get('store'), match.get('store', '?'))}: "
        f"{_money(match.get('promo_price'))}**"
        for match in matches
    )

    sections: list[str] = []
    for match in matches:
        store = STORE_NAMES.get(match.get("store"), match.get("store", "?"))
        promo = _money(match.get("promo_price"))
        regular = _money(match.get("regular_price"))
        estimated = "ok. " if match.get("regular_price_estimated") else ""
        date_from = _date_pl(match.get("valid_from"))
        date_to = _date_pl(match.get("valid_to"))
        product = match.get("name") or item.get("summary")
        discount = match.get("discount_percent")
        discount_text = (
            f" · rabat: {float(discount):.0f}%" if discount is not None else ""
        )

        sections.append(
            f"**{store} — PROMOCJA {promo}**  \n"
            f"Cena regularna: {estimated}{regular}{discount_text}  \n"
            f"Ważna: {date_from} – {date_to}  \n"
            f"Dopasowanie: {product}"
        )

    return f"{headline}\n\n" + "\n\n".join(sections)
