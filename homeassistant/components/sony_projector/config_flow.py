"""Config flow for the Sony Projector integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pysdcp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

DOMAIN = "sony_projector"
DEFAULT_TITLE = "Sony Projector"

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_HOST): str})


async def _async_validate_input(hass: HomeAssistant, data: Mapping[str, Any]) -> None:
    """Validate the host information provided by the user."""

    projector = pysdcp.Projector(data[CONF_HOST])

    try:
        await hass.async_add_executor_job(projector.get_power)
    except ConnectionError as err:
        raise CannotConnect from err
    except OSError as err:
        raise CannotConnect from err
    except Exception as err:
        raise UnknownError from err


class SonyProjectorConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Sony Projector."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initiated by the user."""

        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            try:
                await _async_validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except UnknownError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})

                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={CONF_HOST: host},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_import(
        self, import_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle import from YAML."""

        host = import_data[CONF_HOST]

        await _async_validate_input(self.hass, import_data)

        await self.async_set_unique_id(host)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        self._async_abort_entries_match({CONF_HOST: host})

        data = {CONF_HOST: host}
        if CONF_NAME in import_data:
            data[CONF_NAME] = import_data[CONF_NAME]

        return self.async_create_entry(
            title=DEFAULT_TITLE,
            data=data,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication flow."""

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Mapping[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauthentication by testing connectivity."""

        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        host = entry.data[CONF_HOST]

        if user_input is not None:
            try:
                await _async_validate_input(self.hass, entry.data)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except UnknownError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates=entry.data
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"host": host},
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class UnknownError(HomeAssistantError):
    """Error to indicate an unknown error occurred."""
