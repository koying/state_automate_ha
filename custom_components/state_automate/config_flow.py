"""Config flow for StateAutomate."""
import logging

import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.core import callback
from homeassistant.const import ( # pylint: disable=import-error
    CONF_ENTITY_ID,
)

from .const import (
    DOMAIN,
)
_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class StateAutomateFlowHandler(config_entries.ConfigFlow):
    """Config flow for StateAutomate component."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH


    def __init__(self):
        """Init StateAutomateFlowHandler."""
        self._errors = {}
        self._state_entity_id = None

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        self._is_import = True
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        self._errors = {}

        if user_input is not None:
            self._state_entity_id = str(user_input[CONF_ENTITY_ID])

            await self.async_set_unique_id(f'{DOMAIN}_{self._state_entity_id}')
            # self._abort_if_unique_id_configured()

            _LOGGER.debug(f"async_step_user: {user_input}")
            return self.async_create_entry(
                title=f"State Automate: {self._state_entity_id}",
                data=user_input,
            )

        self._errors["base"] = "use_yaml"
        return self.async_show_form(
            step_id="user",
            errors=self._errors,
        )


