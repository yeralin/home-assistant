"""Google Report State implementation."""
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.const import MATCH_ALL
from homeassistant.helpers.event import async_call_later

from .helpers import AbstractConfig, GoogleEntity, async_get_entities
from .error import SmartHomeError

# Time to wait until the homegraph updates
# https://github.com/actions-on-google/smart-home-nodejs/issues/196#issuecomment-439156639
INITIAL_REPORT_DELAY = 60


_LOGGER = logging.getLogger(__name__)


@callback
def async_enable_report_state(hass: HomeAssistant, google_config: AbstractConfig):
    """Enable state reporting."""

    async def async_entity_state_listener(changed_entity, old_state, new_state):
        if not new_state:
            return

        if not google_config.should_expose(new_state):
            return

        entity = GoogleEntity(hass, google_config, new_state)

        if not entity.is_supported():
            return

        try:
            entity_data = entity.query_serialize()
        except SmartHomeError as err:
            _LOGGER.debug("Not reporting state for %s: %s", changed_entity, err.code)
            return

        if old_state:
            old_entity = GoogleEntity(hass, google_config, old_state)

            # Only report to Google if data that Google cares about has changed
            if entity_data == old_entity.query_serialize():
                return

        await google_config.async_report_state(
            {"devices": {"states": {changed_entity: entity_data}}}
        )

    async_call_later(
        hass, INITIAL_REPORT_DELAY, _async_report_all_states(hass, google_config)
    )

    return hass.helpers.event.async_track_state_change(
        MATCH_ALL, async_entity_state_listener
    )


async def _async_report_all_states(hass: HomeAssistant, google_config: AbstractConfig):
    """Report all states."""
    entities = {}

    for entity in async_get_entities(hass, google_config):
        if not entity.should_expose():
            continue

        entities[entity.entity_id] = entity.query_serialize()

    await google_config.async_report_state({"devices": {"states": entities}})
