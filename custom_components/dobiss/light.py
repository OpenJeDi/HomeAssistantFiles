"""Dobiss Light Control"""
import logging
import voluptuous as vol
from .dobiss import DobissSystem
from .const import DOMAIN

from homeassistant.components.light import SUPPORT_FLASH, SUPPORT_TRANSITION, SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS, LightEntity, PLATFORM_SCHEMA
from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)


_LOGGER = logging.getLogger(__name__)

        
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup the Dobiss Light platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]

    _LOGGER.info("Adding lights...")

    # Add devices
    #add_devices(HomeAssistantDobissLight(light, dobiss) for light in dobiss.lights)
    #add_devices(HomeAssistantDobissFan(fan, dobiss) for fan in dobiss.fans)
    #add_devices(HomeAssistantDobissLight(light, dobiss) for light in dobiss.outputs) # TEMP Everything as a light
    async_add_entities(
        HomeAssistantDobissLight(coordinator, light) for light in coordinator.dobiss.outputs # TEMP Everything as a light
    )
    
    _LOGGER.info("Dobiss entities added.")


class HomeAssistantDobissLight(CoordinatorEntity, LightEntity):
    """Representation of a Dobiss light in HomeAssistant."""

    def __init__(self, coordinator, light):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

        """Initialize a DobissLight."""
        self.dobiss = coordinator.dobiss
        self._light = light
        self._name = light['name']

    @property
    def supported_features(self):
        if self.dobiss.modules[self._light['moduleAddress']]['type'] == DobissSystem.ModuleType.Relais:
            return (SUPPORT_FLASH | SUPPORT_TRANSITION)
        else:
            return (SUPPORT_FLASH | SUPPORT_TRANSITION | SUPPORT_BRIGHTNESS)

    @property
    def unique_id(self):
        return "{}.{}".format(self._light['moduleAddress'], self._light['index'])

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._light
    
    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        val = self.coordinator.data[self._light['moduleAddress']][self._light['index']]
        return int(val * 255 / 100)

    @property
    def is_on(self):
        """Return true if light is on."""
        val = self.coordinator.data[self._light['moduleAddress']][self._light['index']]
        return (val > 0)

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        pct = int(kwargs.get(ATTR_BRIGHTNESS, 255) * 100 / 255)
        if self.dobiss.connect(True): # Retry until connected
            self.dobiss.setOn(self._light['moduleAddress'], self._light['index'], pct)
            self.dobiss.disconnect()

            # Poll states
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        if self.dobiss.connect(True): # Retry until connected
            self.dobiss.setOff(self._light['moduleAddress'], self._light['index'])
            self.dobiss.disconnect()

            # Poll states
            await self.coordinator.async_request_refresh()


class HomeAssistantDobissFan(SwitchDevice):
    """Representation of a Dobiss fan in HomeAssistant."""

    def __init__(self, fan, dobiss):
        """Initialize a DobissFan."""
        self._fan = fan
        self._name = fan['name']
        self._state = None

        # We keep a separate connection for each output for now
        self.dobiss = DobissSystem(dobiss.host, dobiss.port)
        self.dobiss.modules = dobiss.modules
        self.dobiss.outputs = dobiss.outputs
        self.dobiss.values = dobiss.values


    @property
    def unique_id(self):
        return "{}.{}".format(self._fan['moduleAddress'], self._fan['index'])

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        return self._fan
    
    @property
    def name(self):
        """Return the display name of this fan."""
        return self._name

    @property
    def is_on(self):
        """Return true if the fan is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Instruct the fan to turn on.
        """
        pct = int(kwargs.get(ATTR_BRIGHTNESS, 255) * 100 / 255)
        if self.dobiss.connect(True): # Retry until connected
            self.dobiss.setOn(self._fan['moduleAddress'], self._fan['index'])
            self.dobiss.disconnect()

    def turn_off(self, **kwargs):
        """Instruct the fan to turn off."""
        if self.dobiss.connect(True): # Retry until connected
            self.dobiss.setOff(self._fan['moduleAddress'], self._fan['index'])
            self.dobiss.disconnect()

    def update(self):
        """Fetch new state data for this fan.

        This is the only method that should fetch new data for Home Assistant.
        """
        # We need to request the status of a complete module
        # TODO Optimise this: now every output of the module triggers this
        module = self.dobiss.modules[self._fan['moduleAddress']]
        if self.dobiss.connect(False): # Don't retry until connected
            self.dobiss.requestStatus(module['address'], module['type'], module['outputCount'])
            self.dobiss.disconnect()

        val = self.dobiss.values[self._fan['moduleAddress']][self._fan['index']]
        self._state = (val > 0)
