"""Provides device automations for Cover."""
from typing import Any, Dict, List
import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_CONDITION,
    CONF_DOMAIN,
    CONF_TYPE,
    CONF_DEVICE_ID,
    CONF_ENTITY_ID,
    STATE_OPEN,
    STATE_CLOSED,
    STATE_OPENING,
    STATE_CLOSING,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition, config_validation as cv, entity_registry
from homeassistant.helpers.typing import ConfigType, TemplateVarsType
from homeassistant.helpers.config_validation import DEVICE_CONDITION_BASE_SCHEMA
from . import DOMAIN

CONDITION_TYPES = {"is_open", "is_closed", "is_opening", "is_closing"}

CONDITION_SCHEMA = DEVICE_CONDITION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_TYPE): vol.In(CONDITION_TYPES),
    }
)


async def async_get_conditions(hass: HomeAssistant, device_id: str) -> List[dict]:
    """List device conditions for Cover devices."""
    registry = await entity_registry.async_get_registry(hass)
    conditions: List[Dict[str, Any]] = []

    # Get all the integrations entities for this device
    for entry in entity_registry.async_entries_for_device(registry, device_id):
        if entry.domain != DOMAIN:
            continue

        # Add conditions for each entity that belongs to this integration
        conditions.append(
            {
                CONF_CONDITION: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "is_open",
            }
        )
        conditions.append(
            {
                CONF_CONDITION: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "is_closed",
            }
        )
        conditions.append(
            {
                CONF_CONDITION: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "is_opening",
            }
        )
        conditions.append(
            {
                CONF_CONDITION: "device",
                CONF_DEVICE_ID: device_id,
                CONF_DOMAIN: DOMAIN,
                CONF_ENTITY_ID: entry.entity_id,
                CONF_TYPE: "is_closing",
            }
        )

    return conditions


def async_condition_from_config(
    config: ConfigType, config_validation: bool
) -> condition.ConditionCheckerType:
    """Create a function to test a device condition."""
    if config_validation:
        config = CONDITION_SCHEMA(config)
    if config[CONF_TYPE] == "is_open":
        state = STATE_OPEN
    elif config[CONF_TYPE] == "is_closed":
        state = STATE_CLOSED
    elif config[CONF_TYPE] == "is_opening":
        state = STATE_OPENING
    elif config[CONF_TYPE] == "is_closing":
        state = STATE_CLOSING

    def test_is_state(hass: HomeAssistant, variables: TemplateVarsType) -> bool:
        """Test if an entity is a certain state."""
        return condition.state(hass, config[ATTR_ENTITY_ID], state)

    return test_is_state
