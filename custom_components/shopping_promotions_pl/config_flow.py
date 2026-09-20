"""Config flow for Shopping Promotions PL."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

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
    STORE_NAMES,
)


def _defaults(config_entry: config_entries.ConfigEntry | None = None) -> dict[str, Any]:
    """Return current configuration values, preferring options over data."""
    if config_entry is None:
        return {
            CONF_SOURCE_TODO: DEFAULT_SOURCE_TODO,
            CONF_STORES: list(DEFAULT_STORES),
            CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
            CONF_MAX_LEAFLETS: DEFAULT_MAX_LEAFLETS,
            CONF_MATCH_THRESHOLD: DEFAULT_MATCH_THRESHOLD,
        }

    values = dict(config_entry.data)
    values.update(config_entry.options)
    return {
        CONF_SOURCE_TODO: values.get(CONF_SOURCE_TODO, DEFAULT_SOURCE_TODO),
        CONF_STORES: list(values.get(CONF_STORES, DEFAULT_STORES)),
        CONF_UPDATE_INTERVAL: int(
            values.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
        CONF_MAX_LEAFLETS: int(values.get(CONF_MAX_LEAFLETS, DEFAULT_MAX_LEAFLETS)),
        CONF_MATCH_THRESHOLD: float(
            values.get(CONF_MATCH_THRESHOLD, DEFAULT_MATCH_THRESHOLD)
        ),
    }


def _schema(values: dict[str, Any]) -> vol.Schema:
    """Build the shared setup/options schema."""
    store_options = [
        selector.SelectOptionDict(value=slug, label=name)
        for slug, name in STORE_NAMES.items()
    ]

    return vol.Schema(
        {
            vol.Required(
                CONF_SOURCE_TODO,
                default=values[CONF_SOURCE_TODO],
            ): selector.EntitySelector(selector.EntitySelectorConfig(domain="todo")),
            vol.Required(
                CONF_STORES,
                default=values[CONF_STORES],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=store_options,
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=values[CONF_UPDATE_INTERVAL],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=48,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(
                CONF_MAX_LEAFLETS,
                default=values[CONF_MAX_LEAFLETS],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1,
                    max=20,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(
                CONF_MATCH_THRESHOLD,
                default=values[CONF_MATCH_THRESHOLD],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.30,
                    max=0.95,
                    step=0.01,
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        }
    )


class ShoppingPromotionsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Shopping Promotions PL."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "ShoppingPromotionsOptionsFlow":
        """Return the options flow."""
        return ShoppingPromotionsOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle initial configuration."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Promocje zakupowe",
                data=user_input,
            )

        return self.async_show_form(step_id="user", data_schema=_schema(_defaults()))


class ShoppingPromotionsOptionsFlow(config_entries.OptionsFlow):
    """Allow changing stores and matching settings after installation."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=_schema(_defaults(self._config_entry)),
        )
