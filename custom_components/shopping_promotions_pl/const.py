"""Constants for Shopping Promotions PL."""
from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "shopping_promotions_pl"
PLATFORMS = [Platform.TODO, Platform.SENSOR]

CONF_SOURCE_TODO = "source_todo"
CONF_STORES = "stores"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_MAX_LEAFLETS = "max_leaflets"
CONF_MATCH_THRESHOLD = "match_threshold"

DEFAULT_SOURCE_TODO = "todo.shopping_list"
DEFAULT_STORES = ["biedronka", "lidl", "auchan", "rossmann"]
STORE_NAMES = {
    "biedronka": "Biedronka",
    "lidl": "Lidl",
    "auchan": "Auchan",
    "rossmann": "Rossmann",
}
DEFAULT_UPDATE_INTERVAL = 6
DEFAULT_MAX_LEAFLETS = 8
DEFAULT_MATCH_THRESHOLD = 0.58

SERVICE_REFRESH = "refresh"
SERVICE_CLEAR_CACHE = "clear_cache"

ATTR_ITEMS = "items"
ATTR_MATCHED_ITEMS = "matched_items"
ATTR_TOTAL_ITEMS = "total_items"
