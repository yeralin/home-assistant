"""Tests for HomematicIP Cloud binary sensor."""
from homematicip.base.enums import SmokeDetectorAlarmType, WindowState

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.homematicip_cloud import DOMAIN as HMIPC_DOMAIN
from homeassistant.components.homematicip_cloud.binary_sensor import (
    ATTR_ACCELERATION_SENSOR_MODE,
    ATTR_ACCELERATION_SENSOR_NEUTRAL_POSITION,
    ATTR_ACCELERATION_SENSOR_SENSITIVITY,
    ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE,
    ATTR_LOW_BATTERY,
    ATTR_MOTION_DETECTED,
)
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.setup import async_setup_component

from .helper import async_manipulate_test_data, get_and_check_entity_basics


async def test_manually_configured_platform(hass):
    """Test that we do not set up an access point."""
    assert (
        await async_setup_component(
            hass,
            BINARY_SENSOR_DOMAIN,
            {BINARY_SENSOR_DOMAIN: {"platform": HMIPC_DOMAIN}},
        )
        is True
    )
    assert not hass.data.get(HMIPC_DOMAIN)


async def test_hmip_acceleration_sensor(hass, default_mock_hap):
    """Test HomematicipAccelerationSensor."""
    entity_id = "binary_sensor.garagentor"
    entity_name = "Garagentor"
    device_model = "HmIP-SAM"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_MODE] == "FLAT_DECT"
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_NEUTRAL_POSITION] == "VERTICAL"
    assert (
        ha_state.attributes[ATTR_ACCELERATION_SENSOR_SENSITIVITY] == "SENSOR_RANGE_4G"
    )
    assert ha_state.attributes[ATTR_ACCELERATION_SENSOR_TRIGGER_ANGLE] == 45
    service_call_counter = len(hmip_device.mock_calls)

    await async_manipulate_test_data(
        hass, hmip_device, "accelerationSensorTriggered", False
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF
    assert len(hmip_device.mock_calls) == service_call_counter + 1

    await async_manipulate_test_data(
        hass, hmip_device, "accelerationSensorTriggered", True
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON
    assert len(hmip_device.mock_calls) == service_call_counter + 2


async def test_hmip_contact_interface(hass, default_mock_hap):
    """Test HomematicipContactInterface."""
    entity_id = "binary_sensor.kontakt_schnittstelle_unterputz_1_fach"
    entity_name = "Kontakt-Schnittstelle Unterputz – 1-fach"
    device_model = "HmIP-FCI1"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "windowState", WindowState.OPEN)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "windowState", None)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_shutter_contact(hass, default_mock_hap):
    """Test HomematicipShutterContact."""
    entity_id = "binary_sensor.fenstergriffsensor"
    entity_name = "Fenstergriffsensor"
    device_model = "HmIP-SRH"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    await async_manipulate_test_data(
        hass, hmip_device, "windowState", WindowState.CLOSED
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF

    await async_manipulate_test_data(hass, hmip_device, "windowState", None)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_motion_detector(hass, default_mock_hap):
    """Test HomematicipMotionDetector."""
    entity_id = "binary_sensor.bewegungsmelder_fur_55er_rahmen_innen"
    entity_name = "Bewegungsmelder für 55er Rahmen – innen"
    device_model = "HmIP-SMI55"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "motionDetected", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_presence_detector(hass, default_mock_hap):
    """Test HomematicipPresenceDetector."""
    entity_id = "binary_sensor.spi_1"
    entity_name = "SPI_1"
    device_model = "HmIP-SPI"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "presenceDetected", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_smoke_detector(hass, default_mock_hap):
    """Test HomematicipSmokeDetector."""
    entity_id = "binary_sensor.rauchwarnmelder"
    entity_name = "Rauchwarnmelder"
    device_model = "HmIP-SWSD"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(
        hass,
        hmip_device,
        "smokeDetectorAlarmType",
        SmokeDetectorAlarmType.PRIMARY_ALARM,
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_water_detector(hass, default_mock_hap):
    """Test HomematicipWaterDetector."""
    entity_id = "binary_sensor.wassersensor"
    entity_name = "Wassersensor"
    device_model = "HmIP-SWD"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "waterlevelDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "moistureDetected", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "waterlevelDetected", True)
    await async_manipulate_test_data(hass, hmip_device, "moistureDetected", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "waterlevelDetected", False)
    await async_manipulate_test_data(hass, hmip_device, "moistureDetected", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON

    await async_manipulate_test_data(hass, hmip_device, "waterlevelDetected", False)
    await async_manipulate_test_data(hass, hmip_device, "moistureDetected", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_storm_sensor(hass, default_mock_hap):
    """Test HomematicipStormSensor."""
    entity_id = "binary_sensor.weather_sensor_plus_storm"
    entity_name = "Weather Sensor – plus Storm"
    device_model = "HmIP-SWO-PL"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "storm", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_rain_sensor(hass, default_mock_hap):
    """Test HomematicipRainSensor."""
    entity_id = "binary_sensor.wettersensor_pro_raining"
    entity_name = "Wettersensor - pro Raining"
    device_model = "HmIP-SWO-PR"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "raining", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_sunshine_sensor(hass, default_mock_hap):
    """Test HomematicipSunshineSensor."""
    entity_id = "binary_sensor.wettersensor_pro_sunshine"
    entity_name = "Wettersensor - pro Sunshine"
    device_model = "HmIP-SWO-PR"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_ON
    assert ha_state.attributes["today_sunshine_duration_in_minutes"] == 100
    await async_manipulate_test_data(hass, hmip_device, "sunshine", False)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_OFF


async def test_hmip_battery_sensor(hass, default_mock_hap):
    """Test HomematicipSunshineSensor."""
    entity_id = "binary_sensor.wohnungsture_battery"
    entity_name = "Wohnungstüre Battery"
    device_model = "HMIP-SWDO"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "lowBat", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON


async def test_hmip_security_zone_sensor_group(hass, default_mock_hap):
    """Test HomematicipSecurityZoneSensorGroup."""
    entity_id = "binary_sensor.internal_securityzone"
    entity_name = "INTERNAL SecurityZone"
    device_model = "HmIP-SecurityZone"

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    await async_manipulate_test_data(hass, hmip_device, "motionDetected", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_MOTION_DETECTED] is True


async def test_hmip_security_sensor_group(hass, default_mock_hap):
    """Test HomematicipSecuritySensorGroup."""
    entity_id = "binary_sensor.buro_sensors"
    entity_name = "Büro Sensors"
    device_model = None

    ha_state, hmip_device = get_and_check_entity_basics(
        hass, default_mock_hap, entity_id, entity_name, device_model
    )

    assert ha_state.state == STATE_OFF
    assert not ha_state.attributes.get("low_bat")
    await async_manipulate_test_data(hass, hmip_device, "lowBat", True)
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON
    assert ha_state.attributes[ATTR_LOW_BATTERY] is True

    await async_manipulate_test_data(hass, hmip_device, "lowBat", False)
    await async_manipulate_test_data(
        hass,
        hmip_device,
        "smokeDetectorAlarmType",
        SmokeDetectorAlarmType.PRIMARY_ALARM,
    )
    ha_state = hass.states.get(entity_id)
    assert ha_state.state == STATE_ON
    assert (
        ha_state.attributes["smoke_detector_alarm"]
        == SmokeDetectorAlarmType.PRIMARY_ALARM
    )
