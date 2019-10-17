"""The tests for the UniFi device tracker platform."""
from copy import copy
from datetime import timedelta

from homeassistant import config_entries
from homeassistant.components import unifi
from homeassistant.components.unifi.const import (
    CONF_SSID_FILTER,
    CONF_TRACK_DEVICES,
    CONF_TRACK_WIRED_CLIENTS,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers import entity_registry
from homeassistant.setup import async_setup_component

import homeassistant.components.device_tracker as device_tracker
import homeassistant.util.dt as dt_util

from .test_controller import ENTRY_CONFIG, SITES, setup_unifi_integration

DEFAULT_DETECTION_TIME = timedelta(seconds=300)

CLIENT_1 = {
    "essid": "ssid",
    "hostname": "client_1",
    "ip": "10.0.0.1",
    "is_wired": False,
    "last_seen": 1562600145,
    "mac": "00:00:00:00:00:01",
}
CLIENT_2 = {
    "hostname": "client_2",
    "ip": "10.0.0.2",
    "is_wired": True,
    "last_seen": 1562600145,
    "mac": "00:00:00:00:00:02",
    "name": "Wired Client",
}
CLIENT_3 = {
    "essid": "ssid2",
    "hostname": "client_3",
    "ip": "10.0.0.3",
    "is_wired": False,
    "last_seen": 1562600145,
    "mac": "00:00:00:00:00:03",
}

DEVICE_1 = {
    "board_rev": 3,
    "device_id": "mock-id",
    "has_fan": True,
    "fan_level": 0,
    "ip": "10.0.1.1",
    "last_seen": 1562600145,
    "mac": "00:00:00:00:01:01",
    "model": "US16P150",
    "name": "device_1",
    "overheating": True,
    "state": 1,
    "type": "usw",
    "upgradable": True,
    "version": "4.0.42.10433",
}
DEVICE_2 = {
    "board_rev": 3,
    "device_id": "mock-id",
    "has_fan": True,
    "ip": "10.0.1.1",
    "mac": "00:00:00:00:01:01",
    "model": "US16P150",
    "name": "device_1",
    "state": 0,
    "type": "usw",
    "version": "4.0.42.10433",
}


async def test_platform_manually_configured(hass):
    """Test that nothing happens when configuring unifi through device tracker platform."""
    assert (
        await async_setup_component(
            hass, device_tracker.DOMAIN, {device_tracker.DOMAIN: {"platform": "unifi"}}
        )
        is False
    )
    assert unifi.DOMAIN not in hass.data


async def test_no_clients(hass):
    """Test the update_clients function when no clients are found."""
    await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={},
        sites=SITES,
        clients_response=[],
        devices_response=[],
        clients_all_response=[],
    )

    assert len(hass.states.async_all()) == 2


async def test_tracked_devices(hass):
    """Test the update_items function with some clients."""
    controller = await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={CONF_SSID_FILTER: ["ssid"]},
        sites=SITES,
        clients_response=[CLIENT_1, CLIENT_2, CLIENT_3],
        devices_response=[DEVICE_1, DEVICE_2],
        clients_all_response={},
    )
    assert len(hass.states.async_all()) == 5

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1 is not None
    assert client_1.state == "not_home"

    client_2 = hass.states.get("device_tracker.wired_client")
    assert client_2 is not None
    assert client_2.state == "not_home"

    client_3 = hass.states.get("device_tracker.client_3")
    assert client_3 is None

    device_1 = hass.states.get("device_tracker.device_1")
    assert device_1 is not None
    assert device_1.state == "not_home"

    client_1_copy = copy(CLIENT_1)
    client_1_copy["last_seen"] = dt_util.as_timestamp(dt_util.utcnow())
    device_1_copy = copy(DEVICE_1)
    device_1_copy["last_seen"] = dt_util.as_timestamp(dt_util.utcnow())
    controller.mock_client_responses.append([client_1_copy])
    controller.mock_device_responses.append([device_1_copy])
    await controller.async_update()
    await hass.async_block_till_done()

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1.state == "home"

    device_1 = hass.states.get("device_tracker.device_1")
    assert device_1.state == "home"

    device_1_copy = copy(DEVICE_1)
    device_1_copy["disabled"] = True
    controller.mock_client_responses.append({})
    controller.mock_device_responses.append([device_1_copy])
    await controller.async_update()
    await hass.async_block_till_done()

    device_1 = hass.states.get("device_tracker.device_1")
    assert device_1.state == STATE_UNAVAILABLE

    controller.config_entry.add_update_listener(controller.async_options_updated)
    hass.config_entries.async_update_entry(
        controller.config_entry,
        options={
            CONF_SSID_FILTER: [],
            CONF_TRACK_WIRED_CLIENTS: False,
            CONF_TRACK_DEVICES: False,
        },
    )
    await hass.async_block_till_done()
    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1
    client_2 = hass.states.get("device_tracker.wired_client")
    assert client_2 is None
    device_1 = hass.states.get("device_tracker.device_1")
    assert device_1 is None


async def test_wireless_client_go_wired_issue(hass):
    """Test the solution to catch wireless device go wired UniFi issue.

    UniFi has a known issue that when a wireless device goes away it sometimes gets marked as wired.
    """
    client_1_client = copy(CLIENT_1)
    client_1_client["last_seen"] = dt_util.as_timestamp(dt_util.utcnow())

    controller = await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={},
        sites=SITES,
        clients_response=[client_1_client],
        devices_response=[],
        clients_all_response=[],
    )
    assert len(hass.states.async_all()) == 3

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1 is not None
    assert client_1.state == "home"

    client_1_client["is_wired"] = True
    client_1_client["last_seen"] = dt_util.as_timestamp(dt_util.utcnow())
    controller.mock_client_responses.append([client_1_client])
    controller.mock_device_responses.append({})
    await controller.async_update()
    await hass.async_block_till_done()

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1.state == "not_home"

    client_1_client["is_wired"] = False
    client_1_client["last_seen"] = dt_util.as_timestamp(dt_util.utcnow())
    controller.mock_client_responses.append([client_1_client])
    controller.mock_device_responses.append({})
    await controller.async_update()
    await hass.async_block_till_done()

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1.state == "home"


async def test_restoring_client(hass):
    """Test the update_items function with some clients."""
    config_entry = config_entries.ConfigEntry(
        version=1,
        domain=unifi.DOMAIN,
        title="Mock Title",
        data=ENTRY_CONFIG,
        source="test",
        connection_class=config_entries.CONN_CLASS_LOCAL_POLL,
        system_options={},
        options={},
        entry_id=1,
    )

    registry = await entity_registry.async_get_registry(hass)
    registry.async_get_or_create(
        device_tracker.DOMAIN,
        unifi.DOMAIN,
        "{}-site_id".format(CLIENT_1["mac"]),
        suggested_object_id=CLIENT_1["hostname"],
        config_entry=config_entry,
    )
    registry.async_get_or_create(
        device_tracker.DOMAIN,
        unifi.DOMAIN,
        "{}-site_id".format(CLIENT_2["mac"]),
        suggested_object_id=CLIENT_2["hostname"],
        config_entry=config_entry,
    )

    await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={unifi.CONF_BLOCK_CLIENT: True},
        sites=SITES,
        clients_response=[CLIENT_2],
        devices_response=[],
        clients_all_response=[CLIENT_1],
    )
    assert len(hass.states.async_all()) == 4

    device_1 = hass.states.get("device_tracker.client_1")
    assert device_1 is not None


async def test_dont_track_clients(hass):
    """Test dont track clients config works."""
    await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={unifi.controller.CONF_TRACK_CLIENTS: False},
        sites=SITES,
        clients_response=[CLIENT_1],
        devices_response=[DEVICE_1],
        clients_all_response=[],
    )
    assert len(hass.states.async_all()) == 3

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1 is None

    device_1 = hass.states.get("device_tracker.device_1")
    assert device_1 is not None
    assert device_1.state == "not_home"


async def test_dont_track_devices(hass):
    """Test dont track devices config works."""
    await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={unifi.controller.CONF_TRACK_DEVICES: False},
        sites=SITES,
        clients_response=[CLIENT_1],
        devices_response=[DEVICE_1],
        clients_all_response=[],
    )
    assert len(hass.states.async_all()) == 3

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1 is not None
    assert client_1.state == "not_home"

    device_1 = hass.states.get("device_tracker.device_1")
    assert device_1 is None


async def test_dont_track_wired_clients(hass):
    """Test dont track wired clients config works."""
    await setup_unifi_integration(
        hass,
        ENTRY_CONFIG,
        options={unifi.controller.CONF_TRACK_WIRED_CLIENTS: False},
        sites=SITES,
        clients_response=[CLIENT_1, CLIENT_2],
        devices_response=[],
        clients_all_response=[],
    )
    assert len(hass.states.async_all()) == 3

    client_1 = hass.states.get("device_tracker.client_1")
    assert client_1 is not None
    assert client_1.state == "not_home"

    client_2 = hass.states.get("device_tracker.client_2")
    assert client_2 is None
