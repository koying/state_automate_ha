"""Config flow for StateAutomate."""
import logging

from homeassistant import config_entries
from homeassistant.util import slugify
from homeassistant.const import ( # pylint: disable=import-error
    CONF_NAME,
    CONF_ENTITY_ID,
)

from .const import (
    CONF_EVENT_TYPE,
    CONF_EVENT_VALUE,
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

    async def async_step_import(self, user_input=None):
        """Handle configuration by yaml file."""
        self._is_import = True
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""

        self._errors = {}
        title = ""

        if user_input is not None:
            if CONF_NAME in user_input:
                await self.async_set_unique_id(f'{DOMAIN}_{slugify(user_input[CONF_NAME])}')
                title = user_input[CONF_NAME]
            elif CONF_ENTITY_ID in user_input:
                await self.async_set_unique_id(f'{DOMAIN}_{user_input[CONF_ENTITY_ID]}')
                title = f"State Automate: {user_input[CONF_ENTITY_ID]}"
            else:
                await self.async_set_unique_id(f'{DOMAIN}_{user_input[CONF_EVENT_TYPE]}_{user_input[CONF_EVENT_VALUE]}')
                title = f"State Automate: {user_input[CONF_EVENT_TYPE]}"
            self._abort_if_unique_id_configured(user_input)

            _LOGGER.debug(f"async_step_user: {user_input}")
            return self.async_create_entry(
                title=title,
                data=user_input,
            )

        self._errors["base"] = "use_yaml"
        return self.async_show_form(
            step_id="user",
            errors=self._errors,
        )


