"""
Sensor for checking the status of Hue sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.hue/
"""
import logging
import re

from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.components.hue import DOMAIN as HUE_DOMAIN
from homeassistant.const import STATE_ON
from .hue_api_response import ENTITY_ATTRS
from .const import DOMAIN, COORDINATOR, BINARIES_ICONS, BINARIES_DEVICE_CLASSES

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""
    coordinator = hass.data[DOMAIN][COORDINATOR]
    devices = []
    for key, entity in coordinator.data.items():
        if entity["model"] == "SML":
            devices.append(HueBinarySensor(key, coordinator))
    async_add_entities(devices, True)


class HueBinarySensor(BinarySensorDevice):
    """Class to hold Hue Sensor basic info."""

    ICON = "mdi:run-fast"

    def __init__(self, hueid, coordinator):
        """Initialize the sensor object."""
        self.hueid = hueid
        self.coordinator = coordinator  # data is in .data
        self.data = self.coordinator.data[self.hueid]   

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.data["name"]

    @property
    def unique_id(self):
        """Return the ID of this Hue sensor."""
        return "{}_{}".format(self.data["model"],self.data["uniqueid"])

    @property
    def is_on(self):
        """Return the state of the sensor."""
        return self.coordinator.data[self.hueid]["state"] == STATE_ON

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        icon = BINARIES_ICONS.get(self.data["model"])
        if icon:
            return icon
        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        device_class = BINARIES_DEVICE_CLASSES.get(self.data["model"])
        if device_class:
            return device_class

    @property
    def device_state_attributes(self):
        """Attributes."""
        return {
            key: self.coordinator.data[self.hueid].get(key) for key in ENTITY_ATTRS.get(self.data["model"], [])
        }

    @property
    def device_info(self):
        """Return the device info."""
        pattern = re.compile(r'(?:[0-9a-fA-F]:?){16}')
        macs  = re.findall(pattern,self.unique_id)
        if len(macs) == 1:
            identifier = macs[0]
        return {
            "name": self.name,
            "identifiers": {(HUE_DOMAIN, identifier),(DOMAIN,identifier)},
            "manufacturer": self.data["manufacturername"],
            "model": self.data["productname"],
        }

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.coordinator.async_add_listener(
            self.async_write_ha_state
        )

    async def async_will_remove_from_hass(self):
        """When entity will be removed from hass."""
        self.coordinator.async_remove_listener(
            self.async_write_ha_state
        )
