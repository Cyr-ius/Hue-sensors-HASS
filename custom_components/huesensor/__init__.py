"""The huesensors component."""
import asyncio
import logging
import aiohue
import async_timeout
from typing import AsyncIterable, List, Tuple
from datetime import timedelta

from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.components.hue import DOMAIN as HUE_DOMAIN, HueBridge

from .const import DOMAIN, COORDINATOR, COMPONENTS
from .hue_api_response import (
    BINARY_SENSOR_MODELS,
    REMOTE_MODELS,
    parse_hue_api_response,
)

SCAN_INTERVAL = timedelta(seconds=0.5)

_LOGGER = logging.getLogger(__name__)

_KNOWN_MODEL_IDS = tuple(BINARY_SENSOR_MODELS + REMOTE_MODELS)

async def async_get_bridges(hass) -> List[HueBridge]:
    """Get Hue bridges."""
    return [
        entry
        for entry in hass.data[HUE_DOMAIN].values()
        if isinstance(entry, HueBridge) and entry.api
    ]

async def async_setup(hass, config):
    """Not implemented."""
    return True

async def async_setup_entry(hass, config_entry):
    """Set up HueSensor as config entry."""
    hass.data[DOMAIN] = {}
    await HueSensorData(hass, config_entry).async_update_info()
    
    for component in COMPONENTS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    hass.async_create_task(
        async_load_platform(hass, "device_tracker", DOMAIN, {}, config_entry)
    )

    return True


class HueSensorData(object):
    """Get the latest sensor data."""

    def __init__(self, hass, config):
        """Initialize the data object."""
        self.hass = hass

    async def async_update_info(self):
        """Get the bridge info."""
        bridges = await async_get_bridges(self.hass)
        await asyncio.gather(
            *[
                bridge.sensor_manager.coordinator.async_request_refresh()
                for bridge in bridges
            ]
        )
        for bridge in bridges:
                await self.async_update_api(bridge)

    async def async_update_api(self,bridge):
        
        self.bridge = bridge

        async def async_update_data():
            """Update sensor data."""
            try:
                with async_timeout.timeout(10):
                    await self.bridge.async_request_call(
                        self.bridge.api.sensors.update
                    )
                    sensors = self.bridge.api.sensors.values()
                    return parse_hue_api_response(
                        sensor.raw
                        for sensor in sensors
                        if sensor.raw["modelid"].startswith(_KNOWN_MODEL_IDS)
                    )   
            except aiohue.Unauthorized:
                await self.bridge.handle_unauthorized_error()
                raise UpdateFailed("Unauthorized")
            except aiohue.AiohueException as err:
                raise UpdateFailed(f"Hue error: {err}")

        self.coordinator = DataUpdateCoordinator(
            self.hass,
            _LOGGER,
            name="sensor",
            update_method=async_update_data,
            update_interval=SCAN_INTERVAL
        )    
        await self.coordinator.async_refresh()

        if not self.coordinator.last_update_success:
            raise PlatformNotReady

        self.hass.data[DOMAIN][COORDINATOR] = self.coordinator
