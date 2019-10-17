"""deCONZ device automation tests."""
from copy import deepcopy

from homeassistant.components.deconz import device_trigger

from tests.common import assert_lists_same, async_get_device_automations

from .test_gateway import ENTRY_CONFIG, DECONZ_WEB_REQUEST, setup_deconz_integration

SENSORS = {
    "1": {
        "config": {
            "alert": "none",
            "battery": 60,
            "group": "10",
            "on": True,
            "reachable": True,
        },
        "ep": 1,
        "etag": "1b355c0b6d2af28febd7ca9165881952",
        "manufacturername": "IKEA of Sweden",
        "mode": 1,
        "modelid": "TRADFRI on/off switch",
        "name": "TRADFRI on/off switch ",
        "state": {"buttonevent": 2002, "lastupdated": "2019-09-07T07:39:39"},
        "swversion": "1.4.018",
        "type": "ZHASwitch",
        "uniqueid": "d0:cf:5e:ff:fe:71:a4:3a-01-1000",
    }
}


async def test_get_triggers(hass):
    """Test triggers work."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["sensors"] = deepcopy(SENSORS)
    gateway = await setup_deconz_integration(
        hass, ENTRY_CONFIG, options={}, get_state_response=data
    )
    device_id = gateway.events[0].device_id
    triggers = await async_get_device_automations(hass, "trigger", device_id)

    expected_triggers = [
        {
            "device_id": device_id,
            "domain": "deconz",
            "platform": "device",
            "type": device_trigger.CONF_SHORT_PRESS,
            "subtype": device_trigger.CONF_TURN_ON,
        },
        {
            "device_id": device_id,
            "domain": "deconz",
            "platform": "device",
            "type": device_trigger.CONF_LONG_PRESS,
            "subtype": device_trigger.CONF_TURN_ON,
        },
        {
            "device_id": device_id,
            "domain": "deconz",
            "platform": "device",
            "type": device_trigger.CONF_LONG_RELEASE,
            "subtype": device_trigger.CONF_TURN_ON,
        },
        {
            "device_id": device_id,
            "domain": "deconz",
            "platform": "device",
            "type": device_trigger.CONF_SHORT_PRESS,
            "subtype": device_trigger.CONF_TURN_OFF,
        },
        {
            "device_id": device_id,
            "domain": "deconz",
            "platform": "device",
            "type": device_trigger.CONF_LONG_PRESS,
            "subtype": device_trigger.CONF_TURN_OFF,
        },
        {
            "device_id": device_id,
            "domain": "deconz",
            "platform": "device",
            "type": device_trigger.CONF_LONG_RELEASE,
            "subtype": device_trigger.CONF_TURN_OFF,
        },
        {
            "device_id": device_id,
            "domain": "sensor",
            "entity_id": "sensor.tradfri_on_off_switch_battery_level",
            "platform": "device",
            "type": "battery_level",
        },
    ]

    assert_lists_same(triggers, expected_triggers)
