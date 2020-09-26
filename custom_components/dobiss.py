import logging
import voluptuous as vol
#import custom_components.light.dobiss as dobiss
from homeassistant.const import CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv

# The domain of your component. Equal to the filename of your component.
DOMAIN = "dobiss"
DATA_DOBISS = DOMAIN

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
##CONFIG_SCHEMA = vol.Schema({
##    DOMAIN: vol.Schema({
##        vol.Required(CONF_HOST): cv.string,
##        vol.Optional(CONF_PORT, default=10001): cv.port
##    }),
##})

def setup(hass, config):
    """Setup the Dobiss system component."""

    # Configuration
    host = config[DOMAIN][CONF_HOST]
    port = config[DOMAIN][CONF_PORT]

    # Connect and disconnect actions
    hass.services.register(DOMAIN, 'connect', connectCall)
    hass.services.register(DOMAIN, 'disconnect', disconnectCall)

    # States
    hass.states.set(DOMAIN+'.host', host, { 'friendly_name': "Installation host" })
    hass.states.set(DOMAIN+'.port', port, { 'friendly_name': "Installation port" })

#    # Connect with the Dobiss system
#    dobiss.connect(host, port)
#    hass.states.set(DOMAIN+'.connected', True, { 'friendly_name': "Connected?" })

    _LOGGER.info("Connected to Dobiss system. Importing installation...")

#    # Import installation
#    dobiss.importFullInstallation()
#    hass.states.set(DOMAIN+'.modulesCount', len(dobiss.modules), { 'friendly_name': "Number of modules" })
#    hass.states.set(DOMAIN+'.outputCount', len(dobiss.outputs), { 'friendly_name': "Number of outputs" })

    _LOGGER.info("Dobiss installation imported.")

#    # Store data to be used in our entities
#    hass.data[DATA_DOBISS] = dobis.__s

    # Return boolean to indicate that initialization was successfully.
    return True


def connectCall(call):
    dobiss.connect(dobiss.__host, dobiss.__port)

def disconnectCall(call):
    dobiss.disconnect()
