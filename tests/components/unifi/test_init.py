"""Test UniFi setup process."""
from unittest.mock import Mock, patch

from homeassistant.components import unifi

from homeassistant.setup import async_setup_component


from tests.common import mock_coro, MockConfigEntry


async def test_setup_with_no_config(hass):
    """Test that we do not discover anything or try to set up a bridge."""
    assert await async_setup_component(hass, unifi.DOMAIN, {}) is True
    assert unifi.DOMAIN not in hass.data
    assert hass.data[unifi.UNIFI_CONFIG] == []


async def test_setup_with_config(hass):
    """Test that we do not discover anything or try to set up a bridge."""
    config = {
        unifi.DOMAIN: {
            unifi.CONF_CONTROLLERS: {
                unifi.CONF_HOST: "1.2.3.4",
                unifi.CONF_SITE_ID: "My site",
                unifi.CONF_BLOCK_CLIENT: ["12:34:56:78:90:AB"],
                unifi.CONF_DETECTION_TIME: 3,
                unifi.CONF_SSID_FILTER: ["ssid"],
            }
        }
    }
    assert await async_setup_component(hass, unifi.DOMAIN, config) is True
    assert unifi.DOMAIN not in hass.data
    assert hass.data[unifi.UNIFI_CONFIG] == [
        {
            unifi.CONF_HOST: "1.2.3.4",
            unifi.CONF_SITE_ID: "My site",
            unifi.CONF_BLOCK_CLIENT: ["12:34:56:78:90:AB"],
            unifi.CONF_DETECTION_TIME: 3,
            unifi.CONF_SSID_FILTER: ["ssid"],
        }
    ]


async def test_successful_config_entry(hass):
    """Test that configured options for a host are loaded via config entry."""
    entry = MockConfigEntry(
        domain=unifi.DOMAIN,
        data={
            "controller": {
                "host": "0.0.0.0",
                "username": "user",
                "password": "pass",
                "port": 80,
                "site": "default",
                "verify_ssl": True,
            },
            "poe_control": True,
        },
    )
    entry.add_to_hass(hass)
    mock_registry = Mock()
    with patch.object(unifi, "UniFiController") as mock_controller, patch(
        "homeassistant.helpers.device_registry.async_get_registry",
        return_value=mock_coro(mock_registry),
    ):
        mock_controller.return_value.async_setup.return_value = mock_coro(True)
        mock_controller.return_value.mac = "00:11:22:33:44:55"
        assert await unifi.async_setup_entry(hass, entry) is True

    assert len(mock_controller.mock_calls) == 2
    p_hass, p_entry = mock_controller.mock_calls[0][1]

    assert p_hass is hass
    assert p_entry is entry

    assert len(mock_registry.mock_calls) == 1
    assert mock_registry.mock_calls[0][2] == {
        "config_entry_id": entry.entry_id,
        "connections": {("mac", "00:11:22:33:44:55")},
        "manufacturer": unifi.ATTR_MANUFACTURER,
        "model": "UniFi Controller",
        "name": "UniFi Controller",
    }


async def test_controller_fail_setup(hass):
    """Test that a failed setup still stores controller."""
    entry = MockConfigEntry(
        domain=unifi.DOMAIN,
        data={
            "controller": {
                "host": "0.0.0.0",
                "username": "user",
                "password": "pass",
                "port": 80,
                "site": "default",
                "verify_ssl": True,
            },
            "poe_control": True,
        },
    )
    entry.add_to_hass(hass)

    with patch.object(unifi, "UniFiController") as mock_cntrlr:
        mock_cntrlr.return_value.async_setup.return_value = mock_coro(False)
        assert await unifi.async_setup_entry(hass, entry) is False

    assert hass.data[unifi.DOMAIN] == {}


async def test_controller_no_mac(hass):
    """Test that configured options for a host are loaded via config entry."""
    entry = MockConfigEntry(
        domain=unifi.DOMAIN,
        data={
            "controller": {
                "host": "0.0.0.0",
                "username": "user",
                "password": "pass",
                "port": 80,
                "site": "default",
                "verify_ssl": True,
            },
            "poe_control": True,
        },
    )
    entry.add_to_hass(hass)
    mock_registry = Mock()
    with patch.object(unifi, "UniFiController") as mock_controller, patch(
        "homeassistant.helpers.device_registry.async_get_registry",
        return_value=mock_coro(mock_registry),
    ):
        mock_controller.return_value.async_setup.return_value = mock_coro(True)
        mock_controller.return_value.mac = None
        assert await unifi.async_setup_entry(hass, entry) is True

    assert len(mock_controller.mock_calls) == 2

    assert len(mock_registry.mock_calls) == 0


async def test_unload_entry(hass):
    """Test being able to unload an entry."""
    entry = MockConfigEntry(
        domain=unifi.DOMAIN,
        data={
            "controller": {
                "host": "0.0.0.0",
                "username": "user",
                "password": "pass",
                "port": 80,
                "site": "default",
                "verify_ssl": True,
            },
            "poe_control": True,
        },
    )
    entry.add_to_hass(hass)

    with patch.object(unifi, "UniFiController") as mock_controller, patch(
        "homeassistant.helpers.device_registry.async_get_registry",
        return_value=mock_coro(Mock()),
    ):
        mock_controller.return_value.async_setup.return_value = mock_coro(True)
        mock_controller.return_value.mac = "00:11:22:33:44:55"
        assert await unifi.async_setup_entry(hass, entry) is True

    assert len(mock_controller.return_value.mock_calls) == 1

    mock_controller.return_value.async_reset.return_value = mock_coro(True)
    assert await unifi.async_unload_entry(hass, entry)
    assert len(mock_controller.return_value.async_reset.mock_calls) == 1
    assert hass.data[unifi.DOMAIN] == {}
