"""Tests for the Sony Projector integration setup."""

from __future__ import annotations

from homeassistant.components.sony_projector.const import DATA_DISCOVERY, DOMAIN


async def test_async_setup_entry(
    hass, init_integration, mock_projector_client, mock_discovery_listener
):
    """Test that the integration sets up as expected."""

    assert init_integration.entry_id in hass.data[DOMAIN]
    runtime = hass.data[DOMAIN][init_integration.entry_id]
    assert init_integration.runtime_data is runtime
    assert runtime.client is mock_projector_client
    assert runtime.coordinator.config_entry is init_integration
    mock_discovery_listener.assert_awaited_once()
    assert DATA_DISCOVERY in hass.data[DOMAIN]


async def test_async_unload_entry(hass, init_integration):
    """Test unloading the config entry."""

    assert await hass.config_entries.async_unload(init_integration.entry_id)
    assert init_integration.entry_id not in hass.data[DOMAIN]
