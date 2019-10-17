"""Tests for HomematicIP Cloud sensor."""
from homematicip.base.enums import ValveState

from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.homematicip_cloud.sensor import (
    ATTR_LEFT_COUNTER,
    ATTR_RIGHT_COUNTER,
    ATTR_TEMPERATURE_OFFSET,
    ATTR_WIND_DIRECTION,
    ATTR_WIND_DIRECTION_VARIATION,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, POWER_WATT, TEMP_CELSIUS
from homeassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass):
    """Test that we do not set up an access point."""
    assert (
        await async_setup_component(
            hass, SENSOR_DOMAIN, {SENSOR_DOMAIN: {"platform": HMIPC_DOMAIN}}
        )
        is True
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_accesspoint_status(hass, default_mock_hap):
    """Test HomematicipSwitch."""
    entity_id = "sensor.access_point"
    entity_name = "Access Point"
    device_model = None

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )
    assert hmip_device
    assert ha_state.state == "8.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "%"

    await async_manipulate_test_data(hass, hmip_device, "dutyCycle", 17.3)

    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "17.3"


async def test_hmip_heating_thermostat(hass, default_mock_hap):
    """Test HomematicipHeatingThermostat."""
    entity_id = "sensor.heizkorperthermostat_heating"
    entity_name = "Heizkörperthermostat Heating"
    device_model = "HMIP-eTRV"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "%"
    await async_manipulate_test_data(hass, hmip_device, "valvePosition", 0.37)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "37"

    await async_manipulate_test_data(hass, hmip_device, "valveState", "nn")
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "nn"

    await async_manipulate_test_data(
        hass, hmip_device, "valveState", ValveState.ADAPTION_DONE
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "37"

    await async_manipulate_test_data(hass, hmip_device, "lowBat", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes["icon"] == "mdi:battery-outline"


async def test_hmip_humidity_sensor(hass, default_mock_hap):
    """Test HomematicipHumiditySensor."""
    entity_id = "sensor.bwth_1_humidity"
    entity_name = "BWTH 1 Humidity"
    device_model = "HmIP-BWTH"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "40"
    assert ha_state.attributes["unit_of_measurement"] == "%"
    await async_manipulate_test_data(hass, hmip_device, "humidity", 45)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "45"


async def test_hmip_temperature_sensor1(hass, default_mock_hap):
    """Test HomematicipTemperatureSensor."""
    entity_id = "sensor.bwth_1_temperature"
    entity_name = "BWTH 1 Temperature"
    device_model = "HmIP-BWTH"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "21.0"
    assert ha_state.attributes["unit_of_measurement"] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "actualTemperature", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get("temperature_offset")
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_temperature_sensor2(hass, default_mock_hap):
    """Test HomematicipTemperatureSensor."""
    entity_id = "sensor.heizkorperthermostat_temperature"
    entity_name = "Heizkörperthermostat Temperature"
    device_model = "HMIP-eTRV"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "20.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == TEMP_CELSIUS
    await async_manipulate_test_data(hass, hmip_device, "valveActualTemperature", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"

    assert not ha_state.attributes.get(ATTR_TEMPERATURE_OFFSET)
    await async_manipulate_test_data(hass, hmip_device, "temperatureOffset", 10)
    ha_state = hass.states.get(entity_id)
    assert ha_state.attributes[ATTR_TEMPERATURE_OFFSET] == 10


async def test_hmip_power_sensor(hass, default_mock_hap):
    """Test HomematicipPowerSensor."""
    entity_id = "sensor.flur_oben_power"
    entity_name = "Flur oben Power"
    device_model = "HmIP-BSM"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "0.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == POWER_WATT
    await async_manipulate_test_data(hass, hmip_device, "currentPowerConsumption", 23.5)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "23.5"


async def test_hmip_illuminance_sensor1(hass, default_mock_hap):
    """Test HomematicipIlluminanceSensor."""
    entity_id = "sensor.wettersensor_illuminance"
    entity_name = "Wettersensor Illuminance"
    device_model = "HmIP-SWO-B"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "4890.0"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "lx"
    await async_manipulate_test_data(hass, hmip_device, "illumination", 231)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "231"


async def test_hmip_illuminance_sensor2(hass, default_mock_hap):
    """Test HomematicipIlluminanceSensor."""
    entity_id = "sensor.lichtsensor_nord_illuminance"
    entity_name = "Lichtsensor Nord Illuminance"
    device_model = "HmIP-SLO"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "807.3"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "lx"
    await async_manipulate_test_data(hass, hmip_device, "averageIllumination", 231)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "231"


async def test_hmip_windspeed_sensor(hass, default_mock_hap):
    """Test HomematicipWindspeedSensor."""
    entity_id = "sensor.wettersensor_pro_windspeed"
    entity_name = "Wettersensor - pro Windspeed"
    device_model = "HmIP-SWO-PR"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "2.6"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "km/h"
    await async_manipulate_test_data(hass, hmip_device, "windSpeed", 9.4)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "9.4"

    assert ha_state.attributes[ATTR_WIND_DIRECTION_VARIATION] == 56.25
    assert ha_state.attributes[ATTR_WIND_DIRECTION] == "WNW"

    wind_directions = {
        25: "NNE",
        37.5: "NE",
        70: "ENE",
        92.5: "E",
        115: "ESE",
        137.5: "SE",
        160: "SSE",
        182.5: "S",
        205: "SSW",
        227.5: "SW",
        250: "WSW",
        272.5: "W",
        295: "WNW",
        317.5: "NW",
        340: "NNW",
        0: "N",
    }

    for direction, txt in wind_directions.items():
        await async_manipulate_test_data(hass, hmip_device, "windDirection", direction)
        ha_state = hass.states.get(entity_id)
        assert ha_state.attributes[ATTR_WIND_DIRECTION] == txt


async def test_hmip_today_rain_sensor(hass, default_mock_hap):
    """Test HomematicipTodayRainSensor."""
    entity_id = "sensor.weather_sensor_plus_today_rain"
    entity_name = "Weather Sensor – plus Today Rain"
    device_model = "HmIP-SWO-PL"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "3.9"
    assert ha_state.attributes[ATTR_UNIT_OF_MEASUREMENT] == "mm"
    await async_manipulate_test_data(hass, hmip_device, "todayRainCounter", 14.2)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "14.2"


async def test_hmip_passage_detector_delta_counter(hass, default_mock_hap):
    """Test HomematicipPassageDetectorDeltaCounter."""
    entity_id = "sensor.spdr_1"
    entity_name = "SPDR_1"
    device_model = "HmIP-SPDR"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == "164"
    assert ha_state.attributes[ATTR_LEFT_COUNTER] == 966
    assert ha_state.attributes[ATTR_RIGHT_COUNTER] == 802
    await async_manipulate_test_data(hass, hmip_device, "leftRightCounterDelta", 190)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == "190"
