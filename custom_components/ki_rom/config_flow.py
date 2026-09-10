"""Oppsettsflyt for KI Rom."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AREAS,
    CONF_EXCLUDE,
    CONF_INCLUDE_CATEGORY,
    CONF_INCLUDE_GROUPS,
    DOMAIN,
    NAVN,
    TRACKED_DOMAINS,
)

SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_AREAS): selector.AreaSelector(
            selector.AreaSelectorConfig(multiple=True)
        ),
        vol.Optional(CONF_EXCLUDE): selector.EntitySelector(
            selector.EntitySelectorConfig(multiple=True, domain=list(TRACKED_DOMAINS))
        ),
        vol.Optional(CONF_INCLUDE_CATEGORY, default=False): selector.BooleanSelector(),
        vol.Optional(CONF_INCLUDE_GROUPS, default=False): selector.BooleanSelector(),
    }
)


class KiRomConfigFlow(ConfigFlow, domain=DOMAIN):
    """Én instans; alle valg ligger i options."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=NAVN, data={}, options=user_input)

        return self.async_show_form(step_id="user", data_schema=SCHEMA)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return KiRomOptionsFlow()


class KiRomOptionsFlow(OptionsFlow):
    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                SCHEMA, self.config_entry.options
            ),
        )
