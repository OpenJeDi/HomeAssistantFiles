"""Dobiss Fan Control"""
import logging
import voluptuous as vol
from .dobiss import DobissSystem
from .const import DOMAIN

from homeassistant.components.fan import FanEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity


_LOGGER = logging.getLogger(__name__)

        
async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup the Dobiss Fan platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]

    fans = coordinator.dobiss.fans
    _LOGGER.info("Adding fans...")
    _LOGGER.debug(str(fans))

    # Add devices
    async_add_entities(
        HomeAssistantDobissFan(coordinator, fan) for fan in fans
    )
    
    _LOGGER.info("Dobiss fans added.")


class HomeAssistantDobissFan(CoordinatorEntity, FanEntity):
    """Representation of a Dobiss fan in HomeAssistant."""

    def __init__(self, coordinator, fan):
        """Pass coordinator to CoordinatorEntity."""
        super().__init__(coordinator)

        """Initialize a DobissFan."""
        self.dobiss = coordinator.dobiss
        self._fan = fan
        self._name = fan['name']


    @property
    def unique_id(self):
        return "{}.{}".format(self._fan['moduleAddress'], self._fan['index'])

    @property
    def device_extra_attributes(self):
        """Return device specific state attributes."""
        return self._fan
    
    @property
    def name(self):
        """Return the display name of this fan."""
        return self._name

    @property
    def is_on(self):
        """Return true if the fan is on."""
        val = self.coordinator.data[self._fan['moduleAddress']][self._fan['index']]
        return (val > 0)

    async def async_turn_on(self, **kwargs):
        """Instruct the fan to turn on.
        """
        self.dobiss.setOn(self._fan['moduleAddress'], self._fan['index'])

        # Poll states
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        """Instruct the fan to turn off."""
        self.dobiss.setOff(self._fan['moduleAddress'], self._fan['index'])

        # Poll states
        await self.coordinator.async_request_refresh()
