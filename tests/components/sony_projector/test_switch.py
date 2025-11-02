from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.sony_projector import DOMAIN, switch
from homeassistant.components.sony_projector.switch import SonyProjectorSwitch
from homeassistant.const import CONF_HOST, CONF_NAME, STATE_ON
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry

TEST_HOST = "198.51.100.15"


async def test_async_setup_entry_adds_entity(hass: HomeAssistant) -> None:
    """Ensure the switch entity is added during config entry setup."""

    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: TEST_HOST, CONF_NAME: "Projector"}
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dict(entry.data)

    projector = MagicMock()
    added_entities: list[SonyProjectorSwitch] = []
    update_flags: list[bool] = []

    def _async_add_entities(entities, update_before_add=False):
        added_entities.extend(entities)
        update_flags.append(update_before_add)

    executor_mock = AsyncMock(side_effect=[STATE_ON, STATE_ON])

    with patch(
        "homeassistant.components.sony_projector.switch.pysdcp.Projector",
        return_value=projector,
    ) as projector_cls, patch.object(
        hass, "async_add_executor_job", executor_mock
    ):
        await switch.async_setup_entry(hass, entry, _async_add_entities)

        projector_cls.assert_called_once_with(TEST_HOST)
        assert executor_mock.await_count == 1
        first_call = executor_mock.await_args_list[0]
        assert first_call.args == (projector.get_power,)
        assert update_flags == [True]
        assert len(added_entities) == 1
        entity = added_entities[0]
        assert isinstance(entity, SonyProjectorSwitch)
        assert entity.unique_id == TEST_HOST
        assert entity.name == "Projector"

        await entity.async_update()

        assert executor_mock.await_count == 2
        assert executor_mock.await_args_list[1].args == (projector.get_power,)
        assert entity.is_on


async def test_async_setup_entry_connection_error(hass: HomeAssistant) -> None:
    """Ensure no entities are added when the initial connection fails."""

    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: TEST_HOST})
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = dict(entry.data)

    async_add_entities = MagicMock()

    with patch(
        "homeassistant.components.sony_projector.switch.pysdcp.Projector",
    ) as projector_cls, patch.object(
        hass,
        "async_add_executor_job",
        AsyncMock(side_effect=ConnectionError),
    ):
        await switch.async_setup_entry(hass, entry, async_add_entities)

    projector_cls.assert_called_once_with(TEST_HOST)
    async_add_entities.assert_not_called()


async def test_switch_async_update_sets_state(hass: HomeAssistant) -> None:
    """Ensure the switch polls the projector using the executor."""

    projector = MagicMock()
    entity = SonyProjectorSwitch(hass, projector=projector, name="Projector", host=TEST_HOST)

    with patch.object(
        hass, "async_add_executor_job", AsyncMock(return_value=STATE_ON)
    ) as executor_mock:
        await entity.async_update()

    executor_mock.assert_awaited_once_with(projector.get_power)
    assert entity.is_on
    assert entity.available


async def test_switch_async_update_handles_error(hass: HomeAssistant) -> None:
    """Ensure availability is cleared when polling fails."""

    projector = MagicMock()
    entity = SonyProjectorSwitch(hass, projector=projector, name="Projector", host=TEST_HOST)

    with patch.object(
        hass, "async_add_executor_job", AsyncMock(side_effect=ConnectionError)
    ) as executor_mock:
        await entity.async_update()

    executor_mock.assert_awaited_once_with(projector.get_power)
    assert not entity.available


async def test_switch_turn_on_updates_state(hass: HomeAssistant) -> None:
    """Ensure the switch uses the executor when turning on."""

    projector = MagicMock()
    entity = SonyProjectorSwitch(hass, projector=projector, name="Projector", host=TEST_HOST)

    executor_mock = AsyncMock(return_value=True)

    with patch.object(entity, "async_write_ha_state") as write_state, patch.object(
        hass, "async_add_executor_job", executor_mock
    ):
        await entity.async_turn_on()

    executor_mock.assert_awaited_once_with(projector.set_power, True)
    write_state.assert_called_once()
    assert entity.is_on
    assert entity.available


async def test_switch_turn_on_failure_marks_unavailable(hass: HomeAssistant) -> None:
    """Ensure failures while turning on mark the entity unavailable."""

    projector = MagicMock()
    entity = SonyProjectorSwitch(hass, projector=projector, name="Projector", host=TEST_HOST)

    executor_mock = AsyncMock(side_effect=ConnectionError)

    with patch.object(entity, "async_write_ha_state") as write_state, patch.object(
        hass, "async_add_executor_job", executor_mock
    ):
        await entity.async_turn_on()

    executor_mock.assert_awaited_once_with(projector.set_power, True)
    write_state.assert_not_called()
    assert not entity.available


async def test_switch_turn_off_updates_state(hass: HomeAssistant) -> None:
    """Ensure the switch uses the executor when turning off."""

    projector = MagicMock()
    entity = SonyProjectorSwitch(hass, projector=projector, name="Projector", host=TEST_HOST)

    executor_mock = AsyncMock(return_value=True)

    with patch.object(entity, "async_write_ha_state") as write_state, patch.object(
        hass, "async_add_executor_job", executor_mock
    ):
        await entity.async_turn_off()

    executor_mock.assert_awaited_once_with(projector.set_power, False)
    write_state.assert_called_once()
    assert not entity.is_on
    assert entity.available


async def test_switch_turn_off_failure_marks_unavailable(hass: HomeAssistant) -> None:
    """Ensure failures while turning off mark the entity unavailable."""

    projector = MagicMock()
    entity = SonyProjectorSwitch(hass, projector=projector, name="Projector", host=TEST_HOST)

    executor_mock = AsyncMock(side_effect=ConnectionError)

    with patch.object(entity, "async_write_ha_state") as write_state, patch.object(
        hass, "async_add_executor_job", executor_mock
    ):
        await entity.async_turn_off()

    executor_mock.assert_awaited_once_with(projector.set_power, False)
    write_state.assert_not_called()
    assert not entity.available
