"""Support for HomematicIP Cloud climate devices."""
import logging
from typing import Awaitable

from homematicip.aio.device import AsyncHeatingThermostat, AsyncHeatingThermostatCompact
from homematicip.aio.group import AsyncHeatingGroup
from homematicip.base.enums import AbsenceType
from homematicip.functionalHomes import IndoorClimateHome

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_NONE,
    SUPPORT_PRESET_MODE,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS
from homeassistant.core import HomeAssistant

from . import DOMAIN as HMIPC_DOMAIN, HMIPC_HAPID, HomematicipGenericDevice
from .hap import HomematicipHAP

_LOGGER = logging.getLogger(__name__)

HMIP_AUTOMATIC_CM = "AUTOMATIC"
HMIP_MANUAL_CM = "MANUAL"
HMIP_ECO_CM = "ECO"


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the HomematicIP Cloud climate devices."""
    pass


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the HomematicIP climate from a config entry."""
    hap = hass.data[HMIPC_DOMAIN][config_entry.data[HMIPC_HAPID]]
    devices = []
    for device in hap.home.groups:
        if isinstance(device, AsyncHeatingGroup):
            devices.append(HomematicipHeatingGroup(hap, device))

    if devices:
        async_add_entities(devices)


class HomematicipHeatingGroup(HomematicipGenericDevice, ClimateDevice):
    """Representation of a HomematicIP heating group."""

    def __init__(self, hap: HomematicipHAP, device) -> None:
        """Initialize heating group."""
        device.modelType = "Group-Heating"
        self._simple_heating = None
        if device.actualTemperature is None:
            self._simple_heating = _get_first_heating_thermostat(device)
        super().__init__(hap, device)

    @property
    def temperature_unit(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE

    @property
    def target_temperature(self) -> float:
        """Return the temperature we try to reach."""
        return self._device.setPointTemperature

    @property
    def current_temperature(self) -> float:
        """Return the current temperature."""
        if self._simple_heating:
            return self._simple_heating.valveActualTemperature
        return self._device.actualTemperature

    @property
    def current_humidity(self) -> int:
        """Return the current humidity."""
        return self._device.humidity

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode.

        Need to be one of HVAC_MODE_*.
        """
        if self._device.boostMode:
            return HVAC_MODE_AUTO
        if self._device.controlMode == HMIP_MANUAL_CM:
            return HVAC_MODE_HEAT

        return HVAC_MODE_AUTO

    @property
    def hvac_modes(self):
        """Return the list of available hvac operation modes.

        Need to be a subset of HVAC_MODES.
        """
        return [HVAC_MODE_AUTO, HVAC_MODE_HEAT]

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp.

        Requires SUPPORT_PRESET_MODE.
        """
        if self._device.boostMode:
            return PRESET_BOOST
        if self._device.controlMode == HMIP_ECO_CM:
            absence_type = self._home.get_functionalHome(IndoorClimateHome).absenceType
            if absence_type == AbsenceType.VACATION:
                return PRESET_AWAY
            if absence_type in [
                AbsenceType.PERIOD,
                AbsenceType.PERMANENT,
                AbsenceType.PARTY,
            ]:
                return PRESET_ECO

        return PRESET_NONE

    @property
    def preset_modes(self):
        """Return a list of available preset modes.

        Requires SUPPORT_PRESET_MODE.
        """
        return [PRESET_NONE, PRESET_BOOST]

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self._device.minTemperature

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self._device.maxTemperature

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._device.set_point_temperature(temperature)

    async def async_set_hvac_mode(self, hvac_mode: str) -> Awaitable[None]:
        """Set new target hvac mode."""
        if hvac_mode == HVAC_MODE_AUTO:
            await self._device.set_control_mode(HMIP_AUTOMATIC_CM)
        else:
            await self._device.set_control_mode(HMIP_MANUAL_CM)

    async def async_set_preset_mode(self, preset_mode: str) -> Awaitable[None]:
        """Set new preset mode."""
        if self._device.boostMode and preset_mode != PRESET_BOOST:
            await self._device.set_boost(False)
        if preset_mode == PRESET_BOOST:
            await self._device.set_boost()


def _get_first_heating_thermostat(heating_group: AsyncHeatingGroup):
    """Return the first HeatingThermostat from a HeatingGroup."""
    for device in heating_group.devices:
        if isinstance(device, (AsyncHeatingThermostat, AsyncHeatingThermostatCompact)):
            return device
    return None
