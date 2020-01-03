"""The huesensors component."""
import asyncio
from datetime import timedelta
import logging
import threading

import aiohue
import async_timeout

from homeassistant.components import hue
from homeassistant.components.hue.bridge import HueBridge
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)
from homeassistant.helpers.event import async_track_time_interval

TYPE_GEOFENCE = "Geofence"
SCAN_INTERVAL = timedelta(seconds=0.5)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Not implemented."""

    return True


async def async_setup_entry(hass, config_entry):
    """Set up HueSensor as config entry."""

    device_registry = await dr.async_get_registry(hass)

    hass.data["huesensor"] = {"data": set()}

    data = HueSensorData(hass, config_entry)
    await data.async_update_info()
    async_track_time_interval(hass, data.async_update_info, SCAN_INTERVAL)

    @callback
    def async_register_hue(unique_id):
        """Hack for register device in both domain (huesensor and hue)."""
        this_device = device_registry.async_get_device({(hue.DOMAIN, unique_id)}, set())
        for entrie in hass.config_entries.async_entries(hue.DOMAIN):
            if this_device:
                device_registry._async_update_device(
                    this_device.id, add_config_entry_id=entrie.entry_id
                )

    async_dispatcher_connect(hass, "update-hue", async_register_hue)

    hass.async_create_task(
        async_load_platform(hass, "device_tracker", "huesensor", {}, config_entry)
    )

    return True


class HueSensorData(object):
    """Get the latest sensor data."""

    def __init__(self, hass, config):
        """Initialize the data object."""
        self.hass = hass
        self.config_entry = config
        self.lock = threading.Lock()
        self.data = {}

    def parse_zgp(self, response):
        """Parse the json response for a ZGPSWITCH Hue Tap."""
        TAP_BUTTONS = {34: "1_click", 16: "2_click", 17: "3_click", 18: "4_click"}
        press = response["state"]["buttonevent"]
        if press is None or press not in TAP_BUTTONS:
            button = "No data"
        else:
            button = TAP_BUTTONS[press]

        data = {
            "uniqueid": response["uniqueid"],
            "manufacturername": response["manufacturername"],
            "productname": response["productname"],
            "model": "ZGP",
            "name": response["name"],
            "state": button,
            "last_updated": response["state"]["lastupdated"].split("T"),
        }
        return data

    def parse_rwl(self, response):
        """Parse the json response for a RWL Hue remote."""

        """
            I know it should be _released not _up
            but _hold_up is too good to miss isn't it
        """
        responsecodes = {"0": "_click", "1": "_hold", "2": "_click_up", "3": "_hold_up"}

        button = None
        if response["state"]["buttonevent"]:
            press = str(response["state"]["buttonevent"])
            button = str(press)[0] + responsecodes[press[-1]]

        data = {
            "uniqueid": response["uniqueid"],
            "manufacturername": response["manufacturername"],
            "productname": response["productname"],
            "model": "RWL",
            "name": response["name"],
            "state": button,
            "battery": response["config"]["battery"],
            "on": response["config"]["on"],
            "reachable": response["config"]["reachable"],
            "last_updated": response["state"]["lastupdated"].split("T"),
        }
        return data

    def parse_foh(self, response):
        """Parse the JSON response for a FOHSWITCH (type still = ZGPSwitch)."""
        FOH_BUTTONS = {
            16: "left_upper_press",
            20: "left_upper_release",
            17: "left_lower_press",
            21: "left_lower_release",
            18: "right_lower_press",
            22: "right_lower_release",
            19: "right_upper_press",
            23: "right_upper_release",
            100: "double_upper_press",
            101: "double_upper_release",
            98: "double_lower_press",
            99: "double_lower_release",
        }

        press = response["state"]["buttonevent"]
        if press is None or press not in FOH_BUTTONS:
            button = "No data"
        else:
            button = FOH_BUTTONS[press]

        data = {
            "uniqueid": response["uniqueid"],
            "manufacturername": response["manufacturername"],
            "productname": response["productname"],
            "model": "FOH",
            "name": response["name"],
            "state": button,
            "last_updated": response["state"]["lastupdated"].split("T"),
        }
        return data

    def parse_z3_rotary(self, response):
        """Parse the json response for a Lutron Aurora Rotary Event."""

        Z3_DIAL = {1: "begin", 2: "end"}

        turn = response["state"]["rotaryevent"]
        dial_position = response["state"]["expectedrotation"]
        if turn is None or turn not in Z3_DIAL:
            dial = "No data"
        else:
            dial = Z3_DIAL[turn]

        data = {
            "uniqueid": response["uniqueid"],
            "manufacturername": response["manufacturername"],
            "productname": response["productname"],
            "model": "Z3-",
            "name": response["name"],
            "dial_state": dial,
            "dial_position": dial_position,
            "software_update": response["swupdate"]["state"],
            "battery": response["config"]["battery"],
            "on": response["config"]["on"],
            "reachable": response["config"]["reachable"],
            "last_updated": response["state"]["lastupdated"].split("T"),
        }
        return data

    def parse_z3_switch(self, response):
        """Parse the json response for a Lutron Aurora."""

        Z3_BUTTON = {
            1000: "initial_press",
            1001: "repeat",
            1002: "short_release",
            1003: "long_release",
        }

        press = response["state"]["buttonevent"]
        if press is None or press not in Z3_BUTTON:
            button = "No data"
        else:
            button = Z3_BUTTON[press]

        data = {
            "uniqueid": response["uniqueid"],
            "manufacturername": response["manufacturername"],
            "productname": response["productname"],
            "state": button,
        }
        return data

    def parse_sml(self, response):
        """Parse the json for a SML Hue motion sensor and return the data."""
        data = {}
        name_raw = response["name"]
        arr = name_raw.split()
        arr.insert(-1, "motion")
        name = " ".join(arr)
        hue_state = response["state"]["presence"]
        if hue_state is True:
            state = STATE_ON
        else:
            state = STATE_OFF

        data = {
            "uniqueid": response["uniqueid"],
            "manufacturername": response["manufacturername"],
            "productname": response["productname"],
            "model": "SML",
            "name": name,
            "state": state,
            "battery": response["config"]["battery"],
            "on": response["config"]["on"],
            "sensitivity": response["config"]["sensitivity"],
            "sensitivity_max": response["config"]["sensitivitymax"],
            "last_updated": response["state"]["lastupdated"].split("T"),
        }
        return data

    def parse_hue_api_response(self, sensors):
        """Take in the Hue API json response."""
        data_dict = {}  # The list of sensors, referenced by their hue_id.

        # Loop over all keys (1,2 etc) to identify sensors and get data.
        for sensor in sensors:
            modelid = sensor["modelid"][0:3]
            if modelid in ["RWL", "ROM", "SML"]:
                _key = modelid + "_" + sensor["uniqueid"][:-5]
                if modelid == "RWL" or modelid == "ROM":
                    data_dict[_key] = self.parse_rwl(sensor)
                if modelid == "SML":
                    if sensor["type"] == "ZLLPresence":
                        data_dict[_key] = self.parse_sml(sensor)

            elif modelid in ["FOH", "ZGP"]:  # New Model ID
                _key = (
                    modelid + "_" + sensor["uniqueid"][-14:-3]
                )  # needed for uniqueness
                if modelid == "FOH":
                    data_dict[_key] = self.parse_foh(sensor)
                elif modelid == "ZGP":
                    data_dict[_key] = self.parse_zgp(sensor)

            elif modelid == "Z3-":
                # Newest Model ID / Lutron Aurora / Hue Bridge treats it as two sensors, I wanted them combined
                if sensor["type"] == "ZLLRelativeRotary":  # Rotary Dial
                    _key = (
                        modelid + "_" + sensor["uniqueid"][:-5]
                    )  # Rotary key is substring of button
                    key_value = self.parse_z3_rotary(sensor)
                else:  # sensor["type"] == "ZLLSwitch"
                    _key = modelid + "_" + sensor["uniqueid"]
                    key_value = self.parse_z3_switch(sensor)

                # Combine parsed data
                if _key in data_dict:
                    data_dict[_key].update(key_value)
                else:
                    data_dict[_key] = key_value

        return data_dict

    def get_bridges(self, hass):
        """Get Hue bridges."""
        return [
            entry
            for entry in hass.data[hue.DOMAIN].values()
            if isinstance(entry, HueBridge) and entry.api
        ]

    async def update_api(self, api):
        """Update data."""
        try:
            with async_timeout.timeout(10):
                await api.update()
        except (asyncio.TimeoutError, aiohue.AiohueException) as err:
            _LOGGER.debug("Failed to fetch sensors: %s", err)
            return False
        return True

    async def update_bridge(self, bridge):
        """Create and update entity."""
        available = await self.update_api(bridge.api.sensors)
        if not available:
            return

        data = self.parse_hue_api_response(
            sensor.raw
            for sensor in bridge.api.sensors.values()
            if sensor.type != TYPE_GEOFENCE
        )

        new_sensors = data.keys() - self.data.keys()
        updated_sensors = []
        for key, new in data.items():
            new["changed"] = True
            old = self.data.get(key)
            if not old or old == new:
                continue
            updated_sensors.append(key)
            if (
                old["last_updated"] == new["last_updated"]
                and old["state"] == new["state"]
            ):
                new["changed"] = False

        self.data.update(data)
        self.hass.data["huesensor"]["data"] = data

        if new_sensors:
            _LOGGER.debug("Created %s", ", ".join(new_sensors))
            self.hass.async_create_task(
                self.hass.config_entries.async_forward_entry_setup(
                    self.config_entry, "sensor"
                )
            )
            self.hass.async_create_task(
                self.hass.config_entries.async_forward_entry_setup(
                    self.config_entry, "binary_sensor"
                )
            )

        for entity_id in updated_sensors:
            _LOGGER.debug(entity_id)
            async_dispatcher_send(
                self.hass, "update-{}".format(entity_id), entity_id, data
            )

    async def async_update_info(self, now=None):
        """Get the bridge info."""
        locked = self.lock.acquire(False)
        if not locked:
            return
        try:
            bridges = self.get_bridges(self.hass)
            if not bridges:
                if now:
                    # periodic task
                    await asyncio.sleep(5)
                return
            await asyncio.wait(
                [self.update_bridge(bridge) for bridge in bridges], loop=self.hass.loop
            )
        finally:
            self.lock.release()
