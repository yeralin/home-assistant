"""Test the Opentherm Gateway config flow."""
import asyncio
from serial import SerialException
from unittest.mock import patch

from homeassistant import config_entries, setup
from homeassistant.const import CONF_DEVICE, CONF_ID, CONF_NAME
from homeassistant.components.opentherm_gw.const import DOMAIN

from pyotgw import OTGW_ABOUT
from tests.common import mock_coro


async def test_form_user(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "homeassistant.components.opentherm_gw.async_setup",
        return_value=mock_coro(True),
    ) as mock_setup, patch(
        "homeassistant.components.opentherm_gw.async_setup_entry",
        return_value=mock_coro(True),
    ) as mock_setup_entry, patch(
        "pyotgw.pyotgw.connect",
        return_value=mock_coro({OTGW_ABOUT: "OpenTherm Gateway 4.2.5"}),
    ) as mock_pyotgw_connect, patch(
        "pyotgw.pyotgw.disconnect", return_value=mock_coro(None)
    ) as mock_pyotgw_disconnect:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB0"}
        )

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Test Entry 1"
    assert result2["data"] == {
        CONF_NAME: "Test Entry 1",
        CONF_DEVICE: "/dev/ttyUSB0",
        CONF_ID: "test_entry_1",
    }
    await hass.async_block_till_done()
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pyotgw_connect.mock_calls) == 1
    assert len(mock_pyotgw_disconnect.mock_calls) == 1


async def test_form_import(hass):
    """Test import from existing config."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    with patch(
        "homeassistant.components.opentherm_gw.async_setup",
        return_value=mock_coro(True),
    ) as mock_setup, patch(
        "homeassistant.components.opentherm_gw.async_setup_entry",
        return_value=mock_coro(True),
    ) as mock_setup_entry, patch(
        "pyotgw.pyotgw.connect",
        return_value=mock_coro({OTGW_ABOUT: "OpenTherm Gateway 4.2.5"}),
    ) as mock_pyotgw_connect, patch(
        "pyotgw.pyotgw.disconnect", return_value=mock_coro(None)
    ) as mock_pyotgw_disconnect:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_IMPORT},
            data={CONF_ID: "legacy_gateway", CONF_DEVICE: "/dev/ttyUSB1"},
        )

    assert result["type"] == "create_entry"
    assert result["title"] == "legacy_gateway"
    assert result["data"] == {
        CONF_NAME: "legacy_gateway",
        CONF_DEVICE: "/dev/ttyUSB1",
        CONF_ID: "legacy_gateway",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pyotgw_connect.mock_calls) == 1
    assert len(mock_pyotgw_disconnect.mock_calls) == 1


async def test_form_duplicate_entries(hass):
    """Test duplicate device or id errors."""
    flow1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    flow2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    flow3 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "homeassistant.components.opentherm_gw.async_setup",
        return_value=mock_coro(True),
    ) as mock_setup, patch(
        "homeassistant.components.opentherm_gw.async_setup_entry",
        return_value=mock_coro(True),
    ) as mock_setup_entry, patch(
        "pyotgw.pyotgw.connect",
        return_value=mock_coro({OTGW_ABOUT: "OpenTherm Gateway 4.2.5"}),
    ) as mock_pyotgw_connect, patch(
        "pyotgw.pyotgw.disconnect", return_value=mock_coro(None)
    ) as mock_pyotgw_disconnect:
        result1 = await hass.config_entries.flow.async_configure(
            flow1["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB0"}
        )
        result2 = await hass.config_entries.flow.async_configure(
            flow2["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB1"}
        )
        result3 = await hass.config_entries.flow.async_configure(
            flow3["flow_id"], {CONF_NAME: "Test Entry 2", CONF_DEVICE: "/dev/ttyUSB0"}
        )
    assert result1["type"] == "create_entry"
    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "id_exists"}
    assert result3["type"] == "form"
    assert result3["errors"] == {"base": "already_configured"}
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1
    assert len(mock_pyotgw_connect.mock_calls) == 1
    assert len(mock_pyotgw_disconnect.mock_calls) == 1


async def test_form_connection_timeout(hass):
    """Test we handle connection timeout."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "pyotgw.pyotgw.connect", side_effect=(asyncio.TimeoutError)
    ) as mock_connect:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_NAME: "Test Entry 1", CONF_DEVICE: "socket://192.0.2.254:1234"},
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "timeout"}
    assert len(mock_connect.mock_calls) == 1


async def test_form_connection_error(hass):
    """Test we handle serial connection error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch("pyotgw.pyotgw.connect", side_effect=(SerialException)) as mock_connect:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_NAME: "Test Entry 1", CONF_DEVICE: "/dev/ttyUSB0"}
        )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "serial_error"}
    assert len(mock_connect.mock_calls) == 1
