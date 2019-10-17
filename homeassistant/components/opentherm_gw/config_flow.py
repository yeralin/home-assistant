"""OpenTherm Gateway config flow."""
import asyncio
from serial import SerialException

import pyotgw
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE, CONF_ID, CONF_NAME

import homeassistant.helpers.config_validation as cv

from . import DOMAIN


class OpenThermGwConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """OpenTherm Gateway Config Flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_init(self, info=None):
        """Handle config flow initiation."""
        if info:
            name = info[CONF_NAME]
            device = info[CONF_DEVICE]
            gw_id = cv.slugify(info.get(CONF_ID, name))

            entries = [e.data for e in self.hass.config_entries.async_entries(DOMAIN)]

            if gw_id in [e[CONF_ID] for e in entries]:
                return self._show_form({"base": "id_exists"})

            if device in [e[CONF_DEVICE] for e in entries]:
                return self._show_form({"base": "already_configured"})

            async def test_connection():
                """Try to connect to the OpenTherm Gateway."""
                otgw = pyotgw.pyotgw()
                status = await otgw.connect(self.hass.loop, device)
                await otgw.disconnect()
                return status.get(pyotgw.OTGW_ABOUT)

            try:
                res = await asyncio.wait_for(test_connection(), timeout=10)
            except asyncio.TimeoutError:
                return self._show_form({"base": "timeout"})
            except SerialException:
                return self._show_form({"base": "serial_error"})

            if res:
                return self._create_entry(gw_id, name, device)

        return self._show_form()

    async def async_step_user(self, info=None):
        """Handle manual initiation of the config flow."""
        return await self.async_step_init(info)

    async def async_step_import(self, import_config):
        """
        Import an OpenTherm Gateway device as a config entry.

        This flow is triggered by `async_setup` for configured devices.
        """
        formatted_config = {
            CONF_NAME: import_config.get(CONF_NAME, import_config[CONF_ID]),
            CONF_DEVICE: import_config[CONF_DEVICE],
            CONF_ID: import_config[CONF_ID],
        }
        return await self.async_step_init(info=formatted_config)

    def _show_form(self, errors=None):
        """Show the config flow form with possible errors."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_DEVICE): str,
                    vol.Optional(CONF_ID): str,
                }
            ),
            errors=errors or {},
        )

    def _create_entry(self, gw_id, name, device):
        """Create entry for the OpenTherm Gateway device."""
        return self.async_create_entry(
            title=name, data={CONF_ID: gw_id, CONF_DEVICE: device, CONF_NAME: name}
        )
