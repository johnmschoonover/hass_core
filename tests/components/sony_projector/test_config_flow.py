"""Tests for the Sony Projector config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.sony_projector.config_flow import DEFAULT_TITLE, DOMAIN
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.common import MockConfigEntry

TEST_HOST = "192.0.2.1"


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test that the user step creates an entry when connection succeeds."""

    with patch(
        "homeassistant.components.sony_projector.config_flow.pysdcp.Projector"
    ) as projector_cls:
        projector_cls.return_value.get_power.return_value = True

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: TEST_HOST}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_TITLE
    assert result["data"] == {CONF_HOST: TEST_HOST}
    assert projector_cls.return_value.get_power.call_count >= 1


async def test_user_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test that the user step surfaces connection errors."""

    with patch(
        "homeassistant.components.sony_projector.config_flow.pysdcp.Projector"
    ) as projector_cls:
        projector_cls.return_value.get_power.side_effect = ConnectionError

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_HOST: TEST_HOST}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_import_flow_success(hass: HomeAssistant) -> None:
    """Test importing YAML configuration into a config entry."""

    with patch(
        "homeassistant.components.sony_projector.config_flow.pysdcp.Projector"
    ) as projector_cls:
        projector_cls.return_value.get_power.return_value = True

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_HOST: TEST_HOST, CONF_NAME: "Legacy"},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == DEFAULT_TITLE
    assert result["data"] == {CONF_HOST: TEST_HOST, CONF_NAME: "Legacy"}


async def test_import_flow_duplicate(hass: HomeAssistant) -> None:
    """Test importing YAML configuration that already exists."""

    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: TEST_HOST}, unique_id=TEST_HOST
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.sony_projector.config_flow.pysdcp.Projector"
    ) as projector_cls:
        projector_cls.return_value.get_power.return_value = True

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_HOST: TEST_HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow_success(hass: HomeAssistant) -> None:
    """Test that the reauth flow validates the connection and aborts with success."""

    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: TEST_HOST}, unique_id=TEST_HOST
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.sony_projector.config_flow.pysdcp.Projector"
    ) as projector_cls:
        projector_cls.return_value.get_power.return_value = True

        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reauth_flow_cannot_connect(hass: HomeAssistant) -> None:
    """Test that the reauth flow surfaces connection errors."""

    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: TEST_HOST}, unique_id=TEST_HOST
    )
    entry.add_to_hass(hass)

    with patch(
        "homeassistant.components.sony_projector.config_flow.pysdcp.Projector"
    ) as projector_cls:
        projector_cls.return_value.get_power.side_effect = ConnectionError

        result = await entry.start_reauth_flow(hass)
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={}
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
