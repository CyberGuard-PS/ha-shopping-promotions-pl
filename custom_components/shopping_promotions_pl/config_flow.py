"""Config flow for Shopping Promotions PL."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
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


class ShoppingPromotionsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure Shopping Promotions PL."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle initial configuration."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Promocje zakupowe",
                data=user_input,
            )

        store_options = [
            selector.SelectOptionDict(value=slug, label=name)
            for slug, name in STORE_NAMES.items()
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SOURCE_TODO,
                    default=DEFAULT_SOURCE_TODO,
                ): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="todo")
                ),
                vol.Required(
                    CONF_STORES,
                    default=DEFAULT_STORES,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=store_options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
                vol.Required(
                    CONF_UPDATE_INTERVAL,
                    default=DEFAULT_UPDATE_INTERVAL,
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
                    default=DEFAULT_MAX_LEAFLETS,
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
                    default=DEFAULT_MATCH_THRESHOLD,
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
        return self.async_show_form(step_id="user", data_schema=schema)
