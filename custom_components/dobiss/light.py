"""Dobiss Light Control"""
import logging
# import voluptuous as vol
from .dobiss import DobissSystem
from .const import DOMAIN
import asyncio

from homeassistant.components.light import SUPPORT_BRIGHTNESS, ATTR_BRIGHTNESS, LightEntity, LightEntityFeature, \
    ColorMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Setup the Dobiss Light platform."""
    coordinator = hass.data[DOMAIN]["coordinator"]

    lights = coordinator.dobiss.lights
    _LOGGER.info("Adding lights...")
    _LOGGER.debug(str(lights))

    # Add devices
    async_add_entities(
        HomeAssistantDobissLight(coordinator, light) for light in lights
    )

    _LOGGER.info("Dobiss lights added.")


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
            return LightEntityFeature.FLASH | LightEntityFeature.TRANSITION
        else:
            # TODO: what else then?
            return LightEntityFeature.FLASH | LightEntityFeature.TRANSITION | SUPPORT_BRIGHTNESS

    @property
    def unique_id(self):
        return f"{self._light['moduleAddress']}.{self._light['index']}"

    @property
    def device_extra_attributes(self):
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
        return val > 0

    async def async_turn_on(self, **kwargs):
        """Instruct the light to turn on.

        You can skip the brightness part if your light does not support
        brightness control.
        """
        pct = int(kwargs.get(ATTR_BRIGHTNESS, 255) * 100 / 255)
        self.dobiss.setOn(self._light['moduleAddress'], self._light['index'], pct)
        await self.coordinator.async_request_refresh()

    @property
    def supported_color_modes(self):
        return [ColorMode.ONOFF]

    @property
    def color_mode(self):
        return ColorMode.ONOFF

    async def async_turn_off(self, **kwargs):
        """Instruct the light to turn off."""
        self.dobiss.setOff(self._light['moduleAddress'], self._light['index'])
        await self.coordinator.async_request_refresh()
