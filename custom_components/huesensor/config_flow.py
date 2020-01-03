"""Config flow to configure Philips Hue."""
import logging

from homeassistant import config_entries

_LOGGER = logging.getLogger(__name__)


class HueSensorFlowHandler(config_entries.ConfigFlow, domain="huesensor"):
    """Handle a Hue config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialize the Hue flow."""

    async def async_step_import(self, import_config):
        """Import a config entry from configuration.yaml."""
        return self.async_show_form(step_id="user")

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        if user_input is not None:
            return self.async_create_entry(title="Hue sensor advanced", data={})

        return self.async_show_form(step_id="user")
