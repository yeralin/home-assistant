"""deCONZ sensor platform tests."""
from copy import deepcopy

from homeassistant.components import deconz
from homeassistant.setup import async_setup_component

import homeassistant.components.sensor as sensor

from .test_gateway import ENTRY_CONFIG, DECONZ_WEB_REQUEST, setup_deconz_integration

SENSORS = {
    "1": {
        "id": "Light sensor id",
        "name": "Light level sensor",
        "type": "ZHALightLevel",
        "state": {"lightlevel": 30000, "dark": False},
        "config": {"on": True, "reachable": True, "temperature": 10},
        "uniqueid": "00:00:00:00:00:00:00:00-00",
    },
    "2": {
        "id": "Presence sensor id",
        "name": "Presence sensor",
        "type": "ZHAPresence",
        "state": {"presence": False},
        "config": {},
        "uniqueid": "00:00:00:00:00:00:00:01-00",
    },
    "3": {
        "id": "Switch 1 id",
        "name": "Switch 1",
        "type": "ZHASwitch",
        "state": {"buttonevent": 1000},
        "config": {},
        "uniqueid": "00:00:00:00:00:00:00:02-00",
    },
    "4": {
        "id": "Switch 2 id",
        "name": "Switch 2",
        "type": "ZHASwitch",
        "state": {"buttonevent": 1000},
        "config": {"battery": 100},
        "uniqueid": "00:00:00:00:00:00:00:03-00",
    },
    "5": {
        "id": "Daylight sensor id",
        "name": "Daylight sensor",
        "type": "Daylight",
        "state": {"daylight": True, "status": 130},
        "config": {},
        "uniqueid": "00:00:00:00:00:00:00:04-00",
    },
    "6": {
        "id": "Power sensor id",
        "name": "Power sensor",
        "type": "ZHAPower",
        "state": {"current": 2, "power": 6, "voltage": 3},
        "config": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:05-00",
    },
    "7": {
        "id": "Consumption id",
        "name": "Consumption sensor",
        "type": "ZHAConsumption",
        "state": {"consumption": 2, "power": 6},
        "config": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:06-00",
    },
    "8": {
        "id": "CLIP light sensor id",
        "name": "CLIP light level sensor",
        "type": "CLIPLightLevel",
        "state": {"lightlevel": 30000},
        "config": {"reachable": True},
        "uniqueid": "00:00:00:00:00:00:00:07-00",
    },
}


async def test_platform_manually_configured(hass):
    """Test that we do not discover anything or try to set up a gateway."""
    assert (
        await async_setup_component(
            hass, sensor.DOMAIN, {"sensor": {"platform": deconz.DOMAIN}}
        )
        is True
    )
    assert deconz.DOMAIN not in hass.data


async def test_no_sensors(hass):
    """Test that no sensors in deconz results in no sensor entities."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    gateway = await setup_deconz_integration(
        hass, ENTRY_CONFIG, options={}, get_state_response=data
    )
    assert len(gateway.deconz_ids) == 0
    assert len(hass.states.async_all()) == 0


async def test_sensors(hass):
    """Test successful creation of sensor entities."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["sensors"] = deepcopy(SENSORS)
    gateway = await setup_deconz_integration(
        hass, ENTRY_CONFIG, options={}, get_state_response=data
    )
    assert "sensor.light_level_sensor" in gateway.deconz_ids
    assert "sensor.presence_sensor" not in gateway.deconz_ids
    assert "sensor.switch_1" not in gateway.deconz_ids
    assert "sensor.switch_1_battery_level" not in gateway.deconz_ids
    assert "sensor.switch_2" not in gateway.deconz_ids
    assert "sensor.switch_2_battery_level" in gateway.deconz_ids
    assert "sensor.daylight_sensor" in gateway.deconz_ids
    assert "sensor.power_sensor" in gateway.deconz_ids
    assert "sensor.consumption_sensor" in gateway.deconz_ids
    assert "sensor.clip_light_level_sensor" not in gateway.deconz_ids
    assert len(hass.states.async_all()) == 6

    light_level_sensor = hass.states.get("sensor.light_level_sensor")
    assert light_level_sensor.state == "999.8"

    presence_sensor = hass.states.get("sensor.presence_sensor")
    assert presence_sensor is None

    switch_1 = hass.states.get("sensor.switch_1")
    assert switch_1 is None

    switch_1_battery_level = hass.states.get("sensor.switch_1_battery_level")
    assert switch_1_battery_level is None

    switch_2 = hass.states.get("sensor.switch_2")
    assert switch_2 is None

    switch_2_battery_level = hass.states.get("sensor.switch_2_battery_level")
    assert switch_2_battery_level.state == "100"

    daylight_sensor = hass.states.get("sensor.daylight_sensor")
    assert daylight_sensor.state == "dawn"

    power_sensor = hass.states.get("sensor.power_sensor")
    assert power_sensor.state == "6"

    consumption_sensor = hass.states.get("sensor.consumption_sensor")
    assert consumption_sensor.state == "0.002"

    gateway.api.sensors["1"].async_update({"state": {"lightlevel": 2000}})
    gateway.api.sensors["4"].async_update({"config": {"battery": 75}})
    await hass.async_block_till_done()

    light_level_sensor = hass.states.get("sensor.light_level_sensor")
    assert light_level_sensor.state == "1.6"

    switch_2_battery_level = hass.states.get("sensor.switch_2_battery_level")
    assert switch_2_battery_level.state == "75"

    await gateway.async_reset()

    assert len(hass.states.async_all()) == 0


async def test_allow_clip_sensors(hass):
    """Test that CLIP sensors can be allowed."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    data["sensors"] = deepcopy(SENSORS)
    gateway = await setup_deconz_integration(
        hass,
        ENTRY_CONFIG,
        options={deconz.gateway.CONF_ALLOW_CLIP_SENSOR: True},
        get_state_response=data,
    )
    assert "sensor.light_level_sensor" in gateway.deconz_ids
    assert "sensor.presence_sensor" not in gateway.deconz_ids
    assert "sensor.switch_1" not in gateway.deconz_ids
    assert "sensor.switch_1_battery_level" not in gateway.deconz_ids
    assert "sensor.switch_2" not in gateway.deconz_ids
    assert "sensor.switch_2_battery_level" in gateway.deconz_ids
    assert "sensor.daylight_sensor" in gateway.deconz_ids
    assert "sensor.power_sensor" in gateway.deconz_ids
    assert "sensor.consumption_sensor" in gateway.deconz_ids
    assert "sensor.clip_light_level_sensor" in gateway.deconz_ids
    assert len(hass.states.async_all()) == 7

    light_level_sensor = hass.states.get("sensor.light_level_sensor")
    assert light_level_sensor.state == "999.8"

    presence_sensor = hass.states.get("sensor.presence_sensor")
    assert presence_sensor is None

    switch_1 = hass.states.get("sensor.switch_1")
    assert switch_1 is None

    switch_1_battery_level = hass.states.get("sensor.switch_1_battery_level")
    assert switch_1_battery_level is None

    switch_2 = hass.states.get("sensor.switch_2")
    assert switch_2 is None

    switch_2_battery_level = hass.states.get("sensor.switch_2_battery_level")
    assert switch_2_battery_level.state == "100"

    daylight_sensor = hass.states.get("sensor.daylight_sensor")
    assert daylight_sensor.state == "dawn"

    power_sensor = hass.states.get("sensor.power_sensor")
    assert power_sensor.state == "6"

    consumption_sensor = hass.states.get("sensor.consumption_sensor")
    assert consumption_sensor.state == "0.002"

    clip_light_level_sensor = hass.states.get("sensor.clip_light_level_sensor")
    assert clip_light_level_sensor.state == "999.8"


async def test_add_new_sensor(hass):
    """Test that adding a new sensor works."""
    data = deepcopy(DECONZ_WEB_REQUEST)
    gateway = await setup_deconz_integration(
        hass, ENTRY_CONFIG, options={}, get_state_response=data
    )
    assert len(gateway.deconz_ids) == 0

    state_added = {
        "t": "event",
        "e": "added",
        "r": "sensors",
        "id": "1",
        "sensor": deepcopy(SENSORS["1"]),
    }
    gateway.api.async_event_handler(state_added)
    await hass.async_block_till_done()

    assert "sensor.light_level_sensor" in gateway.deconz_ids

    light_level_sensor = hass.states.get("sensor.light_level_sensor")
    assert light_level_sensor.state == "999.8"
