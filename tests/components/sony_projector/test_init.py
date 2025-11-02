"""Tests for the Sony Projector config entry wiring."""

from unittest.mock import AsyncMock, patch

from homeassistant.components import sony_projector
from homeassistant.components.sony_projector import DOMAIN, PLATFORMS
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

TEST_HOST = "192.0.2.10"


async def test_async_setup_entry_stores_data_and_forwards(
    hass: HomeAssistant,
) -> None:
    """Ensure the config entry setup stores data and forwards to platforms."""

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    entry.add_to_hass(hass)

    forward_mock = AsyncMock()

    with patch.object(
        hass.config_entries,
        "async_forward_entry_setups",
        forward_mock,
    ):
        assert await sony_projector.async_setup_entry(hass, entry)

    forward_mock.assert_awaited_once_with(entry, PLATFORMS)
    assert hass.data[DOMAIN][entry.entry_id][CONF_HOST] == TEST_HOST


async def test_async_unload_entry_removes_data(hass: HomeAssistant) -> None:
    """Ensure unloading a config entry cleans up stored data."""

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dict(entry.data)

    unload_mock = AsyncMock(return_value=True)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        unload_mock,
    ):
        assert await sony_projector.async_unload_entry(hass, entry)

    unload_mock.assert_awaited_once_with(entry, PLATFORMS)
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_async_unload_entry_failure_keeps_data(
    hass: HomeAssistant,
) -> None:
    """Ensure stored data remains when platform unloading fails."""

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dict(entry.data)

    unload_mock = AsyncMock(return_value=False)

    with patch.object(
        hass.config_entries,
        "async_unload_platforms",
        unload_mock,
    ):
        assert not await sony_projector.async_unload_entry(hass, entry)

    unload_mock.assert_awaited_once_with(entry, PLATFORMS)
    assert entry.entry_id in hass.data[DOMAIN]
