"""ZHA device automation trigger tests."""
import pytest

import homeassistant.components.automation as automation
from homeassistant.components.switch import DOMAIN
from homeassistant.components.zha.core.const import CHANNEL_ON_OFF
from homeassistant.helpers.device_registry import async_get_registry
from homeassistant.setup import async_setup_component

from .common import async_enable_traffic, async_init_zigpy_device

from tests.common import async_mock_service, async_get_device_automations

ON = 1
OFF = 0
SHAKEN = "device_shaken"
COMMAND = "command"
COMMAND_SHAKE = "shake"
COMMAND_HOLD = "hold"
COMMAND_SINGLE = "single"
COMMAND_DOUBLE = "double"
DOUBLE_PRESS = "remote_button_double_press"
SHORT_PRESS = "remote_button_short_press"
LONG_PRESS = "remote_button_long_press"
LONG_RELEASE = "remote_button_long_release"


def _same_lists(list_a, list_b):
    if len(list_a) != len(list_b):
        return False

    for item in list_a:
        if item not in list_b:
            return False
    return True


@pytest.fixture
def calls(hass):
    """Track calls to a mock serivce."""
    return async_mock_service(hass, "test", "automation")


async def test_triggers(hass, config_entry, zha_gateway):
    """Test zha device triggers."""
    from zigpy.zcl.clusters.general import OnOff, Basic

    # create zigpy device
    zigpy_device = await async_init_zigpy_device(
        hass, [Basic.cluster_id], [OnOff.cluster_id], None, zha_gateway
    )

    zigpy_device.device_automation_triggers = {
        (SHAKEN, SHAKEN): {COMMAND: COMMAND_SHAKE},
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
        (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_HOLD},
    }

    await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await hass.async_block_till_done()
    hass.config_entries._entries.append(config_entry)

    zha_device = zha_gateway.get_device(zigpy_device.ieee)
    ieee_address = str(zha_device.ieee)

    ha_device_registry = await async_get_registry(hass)
    reg_device = ha_device_registry.async_get_device({("zha", ieee_address)}, set())

    triggers = await async_get_device_automations(hass, "trigger", reg_device.id)

    expected_triggers = [
        {
            "device_id": reg_device.id,
            "domain": "zha",
            "platform": "device",
            "type": SHAKEN,
            "subtype": SHAKEN,
        },
        {
            "device_id": reg_device.id,
            "domain": "zha",
            "platform": "device",
            "type": DOUBLE_PRESS,
            "subtype": DOUBLE_PRESS,
        },
        {
            "device_id": reg_device.id,
            "domain": "zha",
            "platform": "device",
            "type": SHORT_PRESS,
            "subtype": SHORT_PRESS,
        },
        {
            "device_id": reg_device.id,
            "domain": "zha",
            "platform": "device",
            "type": LONG_PRESS,
            "subtype": LONG_PRESS,
        },
        {
            "device_id": reg_device.id,
            "domain": "zha",
            "platform": "device",
            "type": LONG_RELEASE,
            "subtype": LONG_RELEASE,
        },
    ]
    assert _same_lists(triggers, expected_triggers)


async def test_no_triggers(hass, config_entry, zha_gateway):
    """Test zha device with no triggers."""
    from zigpy.zcl.clusters.general import OnOff, Basic

    # create zigpy device
    zigpy_device = await async_init_zigpy_device(
        hass, [Basic.cluster_id], [OnOff.cluster_id], None, zha_gateway
    )

    await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await hass.async_block_till_done()
    hass.config_entries._entries.append(config_entry)

    zha_device = zha_gateway.get_device(zigpy_device.ieee)
    ieee_address = str(zha_device.ieee)

    ha_device_registry = await async_get_registry(hass)
    reg_device = ha_device_registry.async_get_device({("zha", ieee_address)}, set())

    triggers = await async_get_device_automations(hass, "trigger", reg_device.id)
    assert triggers == []


async def test_if_fires_on_event(hass, config_entry, zha_gateway, calls):
    """Test for remote triggers firing."""
    from zigpy.zcl.clusters.general import OnOff, Basic

    # create zigpy device
    zigpy_device = await async_init_zigpy_device(
        hass, [Basic.cluster_id], [OnOff.cluster_id], None, zha_gateway
    )

    zigpy_device.device_automation_triggers = {
        (SHAKEN, SHAKEN): {COMMAND: COMMAND_SHAKE},
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
        (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_HOLD},
    }

    await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await hass.async_block_till_done()
    hass.config_entries._entries.append(config_entry)

    zha_device = zha_gateway.get_device(zigpy_device.ieee)

    # allow traffic to flow through the gateway and device
    await async_enable_traffic(hass, zha_gateway, [zha_device])

    ieee_address = str(zha_device.ieee)
    ha_device_registry = await async_get_registry(hass)
    reg_device = ha_device_registry.async_get_device({("zha", ieee_address)}, set())

    assert await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "device_id": reg_device.id,
                        "domain": "zha",
                        "platform": "device",
                        "type": SHORT_PRESS,
                        "subtype": SHORT_PRESS,
                    },
                    "action": {
                        "service": "test.automation",
                        "data": {"message": "service called"},
                    },
                }
            ]
        },
    )

    await hass.async_block_till_done()

    on_off_channel = zha_device.cluster_channels[CHANNEL_ON_OFF]
    on_off_channel.zha_send_event(on_off_channel.cluster, COMMAND_SINGLE, [])
    await hass.async_block_till_done()

    assert len(calls) == 1
    assert calls[0].data["message"] == "service called"


async def test_exception_no_triggers(hass, config_entry, zha_gateway, calls, caplog):
    """Test for exception on event triggers firing."""
    from zigpy.zcl.clusters.general import OnOff, Basic

    # create zigpy device
    zigpy_device = await async_init_zigpy_device(
        hass, [Basic.cluster_id], [OnOff.cluster_id], None, zha_gateway
    )

    await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await hass.async_block_till_done()
    hass.config_entries._entries.append(config_entry)

    zha_device = zha_gateway.get_device(zigpy_device.ieee)

    # allow traffic to flow through the gateway and device
    await async_enable_traffic(hass, zha_gateway, [zha_device])

    ieee_address = str(zha_device.ieee)
    ha_device_registry = await async_get_registry(hass)
    reg_device = ha_device_registry.async_get_device({("zha", ieee_address)}, set())

    await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "device_id": reg_device.id,
                        "domain": "zha",
                        "platform": "device",
                        "type": "junk",
                        "subtype": "junk",
                    },
                    "action": {
                        "service": "test.automation",
                        "data": {"message": "service called"},
                    },
                }
            ]
        },
    )
    await hass.async_block_till_done()
    assert "Invalid config for [automation]" in caplog.text


async def test_exception_bad_trigger(hass, config_entry, zha_gateway, calls, caplog):
    """Test for exception on event triggers firing."""
    from zigpy.zcl.clusters.general import OnOff, Basic

    # create zigpy device
    zigpy_device = await async_init_zigpy_device(
        hass, [Basic.cluster_id], [OnOff.cluster_id], None, zha_gateway
    )

    zigpy_device.device_automation_triggers = {
        (SHAKEN, SHAKEN): {COMMAND: COMMAND_SHAKE},
        (DOUBLE_PRESS, DOUBLE_PRESS): {COMMAND: COMMAND_DOUBLE},
        (SHORT_PRESS, SHORT_PRESS): {COMMAND: COMMAND_SINGLE},
        (LONG_PRESS, LONG_PRESS): {COMMAND: COMMAND_HOLD},
        (LONG_RELEASE, LONG_RELEASE): {COMMAND: COMMAND_HOLD},
    }

    await hass.config_entries.async_forward_entry_setup(config_entry, DOMAIN)
    await hass.async_block_till_done()
    hass.config_entries._entries.append(config_entry)

    zha_device = zha_gateway.get_device(zigpy_device.ieee)

    # allow traffic to flow through the gateway and device
    await async_enable_traffic(hass, zha_gateway, [zha_device])

    ieee_address = str(zha_device.ieee)
    ha_device_registry = await async_get_registry(hass)
    reg_device = ha_device_registry.async_get_device({("zha", ieee_address)}, set())

    await async_setup_component(
        hass,
        automation.DOMAIN,
        {
            automation.DOMAIN: [
                {
                    "trigger": {
                        "device_id": reg_device.id,
                        "domain": "zha",
                        "platform": "device",
                        "type": "junk",
                        "subtype": "junk",
                    },
                    "action": {
                        "service": "test.automation",
                        "data": {"message": "service called"},
                    },
                }
            ]
        },
    )
    await hass.async_block_till_done()
    assert "Invalid config for [automation]" in caplog.text
