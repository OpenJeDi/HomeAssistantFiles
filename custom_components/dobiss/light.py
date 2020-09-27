"""Dobiss Light Control"""
import logging
import voluptuous as vol
from .dobiss import DobissSystem

from homeassistant.components.light import SUPPORT_FLASH, SUPPORT_TRANSITION, SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS, LightEntity, PLATFORM_SCHEMA
from homeassistant.components.switch import (SwitchDevice, PLATFORM_SCHEMA)
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv


# Dependent on the Dobiss system component
#DEPENDENCIES = ['dobiss']

# Home Assistant depends on 3rd party packages for API specific code.
#REQUIREMENTS = ['awesome_lights==1.2.3']

#DOMAIN = 'light'


_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=10001): cv.port
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Dobiss Light platform."""
    
    #hass.services.register(DOMAIN, 'connect', dobiss.connect)
    #hass.services.register(DOMAIN, 'disconnect', dobiss.disconnect)

    # Assign configuration variables. The configuration check takes care they are
    # present.
    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)

    dobiss = DobissSystem(host, port)

    # Connect with the Dobiss system
    #dobiss.connect(host, port)
    dobiss.connect(True) # Retry until connected
    
    _LOGGER.info("Connected to Dobiss system. Importing installation...")
    
    # Import installation
    dobiss.importFullInstallation()
    # We are done, free the connection
    dobiss.disconnect()
    
    _LOGGER.info("Dobiss installation imported. Adding lights...")

    # Disconnect
    #dobiss.disconnect()

    # Verify that passed in configuration works
    #if not hub.is_valid_login():
    #    _LOGGER.error("Could not connect to AwesomeLight hub")
    #    return

    # Add devices
    #add_devices(HomeAssistantDobissLight(light, dobiss) for light in dobiss.lights)
    #add_devices(HomeAssistantDobissFan(fan, dobiss) for fan in dobiss.fans)
    add_devices(HomeAssistantDobissLight(light, dobiss) for light in dobiss.outputs) # TEMP Everything as a light
    
    _LOGGER.info("Dobiss lights added.")


class HomeAssistantDobissLight(LightEntity):
    """Representation of a Dobiss light in HomeAssistant."""

    def __init__(self, light, dobiss):
        """Initialize a DobissLight."""
        self._light = light
        self._name = light['name']
        self._state = None
        self._brightness = None

        # We keep a separate connection for each light for now
        self.dobiss = DobissSystem(dobiss.host, dobiss.port)
        self.dobiss.modules = dobiss.modules
        self.dobiss.outputs = dobiss.outputs
        self.dobiss.values = dobiss.values

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
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    def turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        pct = int(kwargs.get(ATTR_BRIGHTNESS, 255) * 100 / 255)
        if self.dobiss.connect(True): # Retry until connected
            self.dobiss.setOn(self._light['moduleAddress'], self._light['index'], pct)
            self.dobiss.disconnect()

    def turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        if self.dobiss.connect(True): # Retry until connected
            self.dobiss.setOff(self._light['moduleAddress'], self._light['index'])
            self.dobiss.disconnect()

    def update(self):
        """Fetch new state data for this light.

        This is the only method that should fetch new data for Home Assistant.
        """
        # We need to request the status of a complete module
        # TODO Optimise this: now every light of the module triggers this
        module = self.dobiss.modules[self._light['moduleAddress']]
        if self.dobiss.connect(False): # Don't retry until connected
            self.dobiss.requestStatus(module['address'], module['type'], module['outputCount'])
            self.dobiss.disconnect()

        val = self.dobiss.values[self._light['moduleAddress']][self._light['index']]
        self._state = (val > 0)
        self._brightness = int(val * 255 / 100)



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
