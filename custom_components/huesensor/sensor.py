"""
Sensor for checking the status of Hue sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.hue/
"""
import logging

from homeassistant.components.hue import DOMAIN
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect, dispatcher_send
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

ICONS = {
    "SML": "mdi:run",
    "RWL": "mdi:remote",
    "ROM": "mdi:remote",
    "ZGP": "mdi:remote",
    "FOH": "mdi:light-switch",
    "Z3-": "mdi:light-switch",
}
DEVICE_CLASSES = {}
ATTRS = {
    "RWL": ["last_updated", "battery", "on", "reachable"],
    "ROM": ["last_updated", "battery", "on", "reachable"],
    "ZGP": ["last_updated"],
    "FOH": ["last_updated"],
    "Z3-": [
        "last_updated",
        "battery",
        "on",
        "reachable",
        "dial_state",
        "dial_position",
        "software_update",
    ],
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Defer binary sensor setup to the shared sensor module."""

    devices = []
    for key, entity in hass.data["huesensor"]["data"].items():
        if entity["model"] != "SML":
            entity_data = hass.data["huesensor"]["data"]
            devices.append(HueSensor(key, entity_data, hass))
    async_add_entities(devices, True)


class HueSensor(Entity):
    """Class to hold Hue Sensor basic info."""

    ICON = "mdi:run-fast"

    def __init__(self, hue_id, data, hass=None):
        """Initialize the sensor object."""
        self._hue_id = hue_id
        self._data = data  # data is in .data
        # ~ self.my_data = None
        self.my_data = self._data.get(self._hue_id)
        self.hass = hass
        self._unsubs = []

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self.my_data["name"]

    @property
    def unique_id(self):
        """Return the ID of this Hue sensor."""
        return self.my_data["uniqueid"]

    @property
    def state(self):
        """Return the state of the sensor."""
        _LOGGER.debug(f"Update State: {self.name} {self.unique_id}")
        if self.my_data and self.my_data["changed"]:
            return self.my_data["state"]

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        icon = ICONS.get(self.my_data["model"])
        if icon:
            return icon
        return self.ICON

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        device_class = DEVICE_CLASSES.get(self.my_data["model"])
        if device_class:
            return device_class

    @property
    def device_state_attributes(self):
        """Attributes."""
        return {
            key: self.my_data.get(key) for key in ATTRS.get(self.my_data["model"], [])
        }

    @property
    def device_info(self):
        """Return the device info."""
        return {
            "name": self.name,
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": self.my_data["manufacturername"],
            "model": self.my_data["productname"],
        }

    async def async_added_to_hass(self):
        """Connect dispatcher and send for register hue component."""
        dispatcher_send(self.hass, "update-hue", self.unique_id)
        self._unsubs = async_dispatcher_connect(
            self.hass, "update-{}".format(self._hue_id), self.async_update_info
        )

    async def async_will_remove_from_hass(self) -> None:
        """Disconnect entity object when removed."""
        self._unsubs()

    @callback
    def async_update_info(self, hue_id, data):
        """Update entity."""
        self.my_data = data.get(self._hue_id)
        self.async_schedule_update_ha_state()
