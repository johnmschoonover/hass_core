"""The Sony Projector integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    EVENT_HOMEASSISTANT_STARTED,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import ProjectorClient, ProjectorClientError, ProjectorState
from .const import (
    CONF_MODEL,
    CONF_SERIAL,
    DATA_DISCOVERY,
    DEFAULT_NAME,
    DOMAIN,
    SCAN_INTERVAL_SECONDS,
)
from .discovery import async_start_listener

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

DISCOVERY_START_LISTENER_UNSUB = "discovery_listener_unsub"


async def _async_ensure_discovery_listener(hass: HomeAssistant) -> None:
    """Ensure the passive discovery listener is running."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if DATA_DISCOVERY in domain_data:
        return

    protocol = await async_start_listener(hass)
    if protocol is None:
        domain_data.pop(DATA_DISCOVERY, None)


PLATFORMS: list[Platform] = [
    Platform.BUTTON,
    Platform.MEDIA_PLAYER,
    Platform.SELECT,
    Platform.SENSOR,
]


@dataclass(slots=True)
class SonyProjectorRuntimeData:
    """Runtime data stored for each config entry."""

    coordinator: SonyProjectorCoordinator
    client: ProjectorClient


type SonyProjectorConfigEntry = ConfigEntry[SonyProjectorRuntimeData]


class SonyProjectorCoordinator(DataUpdateCoordinator[ProjectorState]):
    """Coordinator to manage projector updates."""

    config_entry: SonyProjectorConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        client: ProjectorClient,
        entry: SonyProjectorConfigEntry,
    ) -> None:
        """Initialize the coordinator."""

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
            config_entry=entry,
        )
        self.client = client
        self.last_error: str | None = None

    async def _async_update_data(self) -> ProjectorState:
        """Fetch data from the projector."""

        try:
            state = await self.client.async_get_state()
        except ProjectorClientError as err:
            self.last_error = str(err)
            raise UpdateFailed(str(err)) from err

        self.last_error = None
        return state


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Sony Projector integration."""

    domain_data = hass.data.setdefault(DOMAIN, {})

    if hass.is_running:
        await _async_ensure_discovery_listener(hass)
    elif DISCOVERY_START_LISTENER_UNSUB not in domain_data:

        async def _start_discovery_listener(_: object) -> None:
            domain_data.pop(DISCOVERY_START_LISTENER_UNSUB, None)
            await _async_ensure_discovery_listener(hass)

        domain_data[DISCOVERY_START_LISTENER_UNSUB] = hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STARTED, _start_discovery_listener
        )

    if (switch_configs := config.get(Platform.SWITCH.value)) is not None:
        for entry in switch_configs:
            if entry.get("platform") != DOMAIN:
                continue

            host = entry.get(CONF_HOST)
            if not host:
                continue

            hass.async_create_task(
                hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "import"},
                    data={
                        CONF_HOST: host,
                        CONF_NAME: entry.get(CONF_NAME, DEFAULT_NAME),
                    },
                )
            )

            _LOGGER.warning(
                "The YAML configuration for sony_projector is deprecated and will be "
                "imported into a config entry. Please remove it from configuration.yaml"
            )

    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: SonyProjectorConfigEntry
) -> bool:
    """Set up Sony Projector from a config entry."""

    domain_data = hass.data.setdefault(DOMAIN, {})
    if unsub := domain_data.pop(DISCOVERY_START_LISTENER_UNSUB, None):
        unsub()

    await _async_ensure_discovery_listener(hass)

    client = ProjectorClient(entry.data[CONF_HOST])
    coordinator = SonyProjectorCoordinator(hass, client, entry)

    await coordinator.async_config_entry_first_refresh()

    runtime = SonyProjectorRuntimeData(
        coordinator=coordinator,
        client=client,
    )
    hass.data[DOMAIN][entry.entry_id] = runtime
    entry.runtime_data = runtime

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    identifier = entry.data.get(CONF_SERIAL) or entry.data[CONF_HOST]
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, identifier)},
        manufacturer="Sony",
        model=entry.data.get(CONF_MODEL),
        name=entry.title,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: SonyProjectorConfigEntry
) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
