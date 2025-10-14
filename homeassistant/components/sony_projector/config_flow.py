"""Config flow for the Sony Projector integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback

from .client import DiscoveredProjector, ProjectorClient, ProjectorClientError, async_discover
from .const import CONF_MODEL, CONF_SERIAL, CONF_TITLE, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class SonyProjectorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sony Projector."""

    VERSION = 1
    _reauth_entry: config_entries.ConfigEntry | None = None
    _discovered: dict[str, DiscoveredProjector]

    async def async_step_user(self, user_input: Mapping[str, Any] | None = None) -> config_entries.FlowResult:
        """Handle the start of the config flow."""

        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "scan"],
        )

    async def async_step_manual(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle manual host configuration."""

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            name = user_input.get(CONF_NAME)
            return await self._async_create_entry_from_host(host, name, "manual")

        data_schema = vol.Schema({vol.Required(CONF_HOST): str, vol.Optional(CONF_NAME): str})
        return self.async_show_form(
            step_id="manual",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_scan(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Handle discovery of projectors on the network."""

        errors: dict[str, str] = {}

        if user_input is not None:
            selected = user_input[CONF_HOST]
            device = self._discovered[selected]
            return await self._async_create_entry_from_host(device.host, device.model, "scan")

        discovered = await async_discover(self.hass.loop)
        current_unique_ids = self._async_current_ids(include_ignore=False)
        filtered: dict[str, DiscoveredProjector] = {}
        for device in discovered:
            unique_id = device.serial or device.host
            if unique_id in current_unique_ids:
                continue
            filtered[device.host] = device

        if not filtered:
            errors["base"] = "no_devices_found"

        self._discovered = filtered

        options = {host: _format_discovery_option(device) for host, device in filtered.items()}

        data_schema = vol.Schema(
            {vol.Required(CONF_HOST): vol.In(options) if options else str}
        )

        return self.async_show_form(
            step_id="scan",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={"count": str(len(filtered))},
        )

    async def async_step_import(self, user_input: Mapping[str, Any]) -> config_entries.FlowResult:
        """Handle YAML import for legacy configurations."""

        host = user_input[CONF_HOST]
        name = user_input.get(CONF_NAME)
        return await self._async_create_entry_from_host(host, name, "manual")

    async def async_step_reauth(self, data: Mapping[str, Any]) -> config_entries.FlowResult:
        """Handle reauthentication."""

        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_user()

    async def _async_create_entry_from_host(
        self,
        host: str,
        suggested_title: str | None,
        source_step: str,
    ) -> config_entries.FlowResult:
        """Validate projector connectivity and create the entry."""

        client = ProjectorClient(host)

        try:
            await client.async_refresh_device_info()
        except ProjectorClientError:
            _LOGGER.debug("Unable to retrieve projector information for host %s", host)

        try:
            await client.async_get_state()
        except ProjectorClientError:
            schema = vol.Schema(
                {vol.Required(CONF_HOST): str, vol.Optional(CONF_NAME): str}
            )
            return self.async_show_form(
                step_id=source_step,
                data_schema=schema,
                errors={"base": "cannot_connect"},
            )

        unique_id = client.serial or host
        await self.async_set_unique_id(unique_id, raise_on_progress=False)

        if self._reauth_entry is not None:
            self._abort_if_unique_id_mismatch(reason="wrong_device")
            return self.async_update_reload_and_abort(
                self._reauth_entry,
                data_updates={
                    CONF_HOST: host,
                    CONF_SERIAL: client.serial,
                    CONF_MODEL: client.model,
                },
            )

        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        title = suggested_title or client.model or DEFAULT_NAME

        return self.async_create_entry(
            title=title,
            data={
                CONF_HOST: host,
                CONF_SERIAL: client.serial,
                CONF_MODEL: client.model,
                CONF_TITLE: title,
            },
        )

    @callback
    def async_get_options_flow(
        self, config_entry: config_entries.ConfigEntry
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""

        return SonyProjectorOptionsFlow(config_entry)


class SonyProjectorOptionsFlow(config_entries.OptionsFlow):
    """Handle options for the Sony Projector integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the options flow."""

        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Mapping[str, Any] | None = None
    ) -> config_entries.FlowResult:
        """Options flow entry point."""

        return self.async_show_form(step_id="init", data_schema=vol.Schema({}))


def _format_discovery_option(device: DiscoveredProjector) -> str:
    """Return a user facing label for a discovered device."""

    serial = device.serial or "unknown"
    model = device.model or DEFAULT_NAME
    return f"{model} ({serial}) @ {device.host}"

