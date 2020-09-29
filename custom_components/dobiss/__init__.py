"""Dobiss Control Systems integration."""
import asyncio
from datetime import timedelta
import logging
import voluptuous as vol

from .dobiss import DobissSystem

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import Config, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

PLATFORMS = ["light", "fan", "switch"]

SCAN_INTERVAL = timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)


# Validation of the user's configuration
# PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
#    vol.Required(CONF_HOST): cv.string,
#    vol.Optional(CONF_PORT, default=10001): cv.port
# })


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Dobiss component from YAML."""

    return True
    
#    # If no settings are found, use config flow
#    if config.get(DOMAIN) is None:
#        return True
#    
#    host = config[DOMAIN].get(CONF_HOST)
#    port = config[DOMAIN].get(CONF_PORT, 10001)
#
#    # We need a host
#    if not host:
#        return False
#
#    success = await setupCoordinator(hass, host, port)
#
#    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Dobiss from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]

    await setupCoordinator(hass, host, port)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def setupCoordinator(hass, host, port):

    coordinator = DobissDataUpdateCoordinator(hass, host=host, port=port)
    await coordinator.async_refresh()    

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["coordinator"] = coordinator

    return True


class DobissDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Dobiss data from the LAN controller."""

    def __init__(self, hass, host, port):
        """Initialize."""
        self.dobiss = DobissSystem(host, port)

        # Connect with the Dobiss system
        #self.dobiss.connect(host, port)
        self.dobiss.connect(True) # Retry until connected
        
        _LOGGER.info("Connected to Dobiss system. Importing installation...")
        
        # Import installation
        self.dobiss.importFullInstallation()
        # We are done, free the connection
        #self.dobiss.disconnect()

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self):
        """Query states"""
        #if self.dobiss.connect(True):
        self.dobiss.requestAllStatus()
            #self.dobiss.disconnect()
        
        return self.dobiss.values
