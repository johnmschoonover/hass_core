"""Support for Sony projectors via SDCP network control."""

from __future__ import annotations

import logging
from typing import Any

import pysdcp
import voluptuous as vol

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Sony Projector"

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up Sony Projector from YAML configuration."""

    hass.async_create_task(
        _async_setup_projector_switch(
            hass,
            host=config[CONF_HOST],
            name=config[CONF_NAME],
            async_add_entities=add_entities,
        )
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sony Projector switches from a config entry."""

    stored = hass.data[DOMAIN].get(entry.entry_id, entry.data)
    name = stored.get(CONF_NAME, DEFAULT_NAME)

    await _async_setup_projector_switch(
        hass,
        host=stored[CONF_HOST],
        name=name,
        async_add_entities=async_add_entities,
    )


async def _async_setup_projector_switch(
    hass: HomeAssistant,
    *,
    host: str,
    name: str,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the projector entity after validating connectivity."""

    projector = pysdcp.Projector(host)

    try:
        await hass.async_add_executor_job(projector.get_power)
    except (ConnectionError, OSError) as err:
        _LOGGER.error("Failed to connect to projector '%s': %s", host, err)
        return

    async_add_entities(
        [SonyProjectorSwitch(hass, projector=projector, name=name, host=host)],
        True,
    )


class SonyProjectorSwitch(SwitchEntity):
    """Represents a Sony Projector as a switch."""

    _attr_should_poll = True

    def __init__(self, hass: HomeAssistant, *, projector, name: str, host: str) -> None:
        """Initialise the Sony projector switch entity."""

        self._hass = hass
        self._projector = projector
        self._host = host
        self._attr_name = name
        self._attr_unique_id = host
        self._attr_is_on = False
        self._attr_available = False

    async def async_update(self) -> None:
        """Fetch the latest state from the projector."""

        try:
            power_state = await self._hass.async_add_executor_job(
                self._projector.get_power
            )
        except (ConnectionError, OSError) as err:
            _LOGGER.error("Failed to update projector '%s': %s", self._host, err)
            self._attr_available = False
            return

        self._attr_available = True
        self._attr_is_on = power_state in (True, STATE_ON)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the projector on."""

        _LOGGER.debug("Powering on projector '%s'", self._host)

        try:
            success = await self._hass.async_add_executor_job(
                self._projector.set_power, True
            )
        except (ConnectionError, OSError) as err:
            _LOGGER.error("Failed to power on projector '%s': %s", self._host, err)
            self._attr_available = False
            return

        if success:
            self._attr_available = True
            self._attr_is_on = True
            self.async_write_ha_state()
        else:
            _LOGGER.error("Power on command was not successful for '%s'", self._host)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the projector off."""

        _LOGGER.debug("Powering off projector '%s'", self._host)

        try:
            success = await self._hass.async_add_executor_job(
                self._projector.set_power, False
            )
        except (ConnectionError, OSError) as err:
            _LOGGER.error("Failed to power off projector '%s': %s", self._host, err)
            self._attr_available = False
            return

        if success:
            self._attr_available = True
            self._attr_is_on = False
            self.async_write_ha_state()
        else:
            _LOGGER.error("Power off command was not successful for '%s'", self._host)
