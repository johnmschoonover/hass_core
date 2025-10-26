"""Tests for the Sony Projector media player platform."""

from __future__ import annotations

from unittest.mock import AsyncMock, call

from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.components.sony_projector import SonyProjectorRuntimeData
from homeassistant.components.sony_projector.const import CONF_TITLE, DEFAULT_NAME, DOMAIN
from homeassistant.components.sony_projector.media_player import (
    PLATFORM_SCHEMA,
    SonyProjectorMediaPlayer,
    async_setup_entry,
    async_setup_platform,
)
from homeassistant.components.sony_projector.client import (
    ProjectorClientError,
    ProjectorState,
)
from homeassistant.const import CONF_HOST, CONF_NAME

from tests.common import MockConfigEntry


def test_platform_schema_allows_name() -> None:
    """Ensure the platform schema accepts optional name overrides."""

    validated = PLATFORM_SCHEMA(
        {"platform": DOMAIN, CONF_HOST: "1.2.3.4", CONF_NAME: "Projector"}
    )
    assert validated[CONF_NAME] == "Projector"


async def test_async_setup_entry_adds_media_player(hass) -> None:
    """Test the config entry setup adds a media player entity."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_TITLE: "Cinema"},
    )
    entry.add_to_hass(hass)
    client = AsyncMock()
    entry.runtime_data = SonyProjectorRuntimeData(client=client)

    added_entities: list[SonyProjectorMediaPlayer] = []

    def _async_add_entities(entities):
        added_entities.extend(entities)

    await async_setup_entry(hass, entry, _async_add_entities)

    assert len(added_entities) == 1
    entity = added_entities[0]
    assert entity.unique_id == "1.2.3.4-media_player"
    assert entity.device_info["name"] == "Cinema"


async def test_media_player_update_success(hass) -> None:
    """Test updating the media player populates state."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_TITLE: "Cinema"},
    )
    client = AsyncMock()
    client.async_get_state.return_value = ProjectorState(is_on=True)

    entity = SonyProjectorMediaPlayer(entry, client)

    await entity.async_update()

    assert entity.available is True
    assert entity.state == MediaPlayerState.ON


async def test_media_player_update_failure_sets_unavailable(hass) -> None:
    """Test update failure marks the entity as unavailable."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_TITLE: DEFAULT_NAME},
    )
    client = AsyncMock()
    client.async_get_state.side_effect = ProjectorClientError

    entity = SonyProjectorMediaPlayer(entry, client)

    await entity.async_update()

    assert entity.available is False
    assert entity.state is None


async def test_media_player_turn_on_off(hass) -> None:
    """Test turning the media player on and off delegates to the client."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_TITLE: "Cinema"},
    )
    client = AsyncMock()

    entity = SonyProjectorMediaPlayer(entry, client)

    await entity.async_turn_on()
    await entity.async_turn_off()

    client.async_set_power.assert_has_awaits([
        call(True),
        call(False),
    ])
    assert entity.available is True
    assert entity.state == MediaPlayerState.OFF


async def test_media_player_turn_on_failure_sets_unavailable(hass) -> None:
    """Test power command failures mark the entity unavailable."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "1.2.3.4", CONF_TITLE: DEFAULT_NAME},
    )
    client = AsyncMock()
    client.async_set_power.side_effect = ProjectorClientError

    entity = SonyProjectorMediaPlayer(entry, client)

    await entity.async_turn_on()

    assert entity.available is False


async def test_async_setup_platform_triggers_import_flow(hass, caplog) -> None:
    """Test YAML platform setup logs a warning and starts an import flow."""

    hass.config_entries.flow.async_init = AsyncMock(return_value=None)
    caplog.set_level("WARNING")

    await async_setup_platform(
        hass,
        {CONF_HOST: "1.2.3.4", CONF_NAME: "Room"},
        lambda entities: None,
    )
    await hass.async_block_till_done()

    hass.config_entries.flow.async_init.assert_awaited_once()
    assert any(
        "deprecated" in record.message for record in caplog.records
    ), "Expected deprecation warning to be logged"


async def test_async_setup_platform_missing_host_logs_error(hass, caplog) -> None:
    """Test missing host entries are reported and not imported."""

    hass.config_entries.flow.async_init = AsyncMock(return_value=None)
    caplog.set_level("ERROR")

    await async_setup_platform(
        hass,
        {CONF_NAME: "Room"},
        lambda entities: None,
    )
    await hass.async_block_till_done()

    assert "Missing 'host'" in caplog.text
    hass.config_entries.flow.async_init.assert_not_called()
