import asyncio
from collections import OrderedDict
import copy
import json
import logging
import glob
from datetime import timedelta
from typing import Any
from typing_extensions import Required

import voluptuous as vol  # pylint: disable=import-error

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (  # pylint: disable=import-error
    CONF_ENTITY_ID,
    CONF_EVENT_DATA,
    CONF_NAME,
    SERVICE_RELOAD,
)
from homeassistant.util import yaml

import homeassistant.helpers.config_validation as cv  # pylint: disable=import-error
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.helpers.dispatcher import (  # pylint: disable=import-error
    async_dispatcher_send,
)
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.service import (
    ReloadServiceHelper,
    async_register_admin_service,
)

from .const import (
    CONF_ACTIVITIES,
    CONF_EVENT_TYPE,
    CONF_EVENT_VALUE,
    CONF_STATES,
    DOMAIN,
    PLATFORMS,
    SIGNAL_STATE_UPDATED,
)

_LOGGER = logging.getLogger(__name__)

UPDATE_UNLISTENER = None


def _ensure_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, OrderedDict):
        ret = json.loads(json.dumps(value))
        # _LOGGER.debug(f"_ensure_dict: {ret}")
        return ret
    if isinstance(value, list):
        ret = {}
        for it in json.loads(json.dumps(value)):
            for k, v in it.items():
                ret[k] = v
        # _LOGGER.debug(f"_ensure_dict: {ret}")
        return ret

    ret = json.loads(json.dumps(value))
    raise vol.Invalid(f"Cannot convert to dict: {type(value)} / {ret}")


def _script_dict(value: Any) -> Any:
    if isinstance(value, dict):
        ret = {key: cv.SCRIPT_SCHEMA(element) for key, element in value.items()}
        # _LOGGER.debug(f"_script_dict: {ret}")
        return ret

    raise vol.Invalid(f"Not a dict: {value}")


ACTIVITY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_STATES): vol.All(_ensure_dict, _script_dict),
    }
)
ENTITY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_ENTITY_ID): cv.entity_id,
        vol.Required(CONF_ACTIVITIES): vol.All(cv.ensure_list, [ACTIVITY_SCHEMA]),
    }
)
EVENT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EVENT_TYPE): cv.string,
        vol.Required(CONF_EVENT_VALUE): cv.string,
        vol.Optional(CONF_EVENT_DATA): vol.All(_ensure_dict),
        vol.Required(CONF_ACTIVITIES): vol.All(cv.ensure_list, [ACTIVITY_SCHEMA]),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(cv.ensure_list, [vol.Any(EVENT_SCHEMA, ENTITY_SCHEMA)]),
    },
    extra=vol.ALLOW_EXTRA,
)

async def _async_process_config(
    hass: HomeAssistant,
    config: dict[str, Any],
    component: EntityComponent,
) -> bool:
    config_yaml = json.loads(json.dumps(config[DOMAIN]))
    _LOGGER.debug(config_yaml)

    for it in config_yaml:
        hass.async_add_job(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_IMPORT}, data=copy.deepcopy(it)
            )
        )

async def async_setup(hass: HomeAssistant, config: dict):
    if DOMAIN not in config:
        return True

    hass.data[DOMAIN] = {}

    component = EntityComponent(_LOGGER, DOMAIN, hass)
    await _async_process_config(hass, config, component)

    async def reload_service_handler(service_call):
        if (conf := await component.async_prepare_reload()) is None:
            return
        await _async_process_config(hass, conf, component)
        hass.bus.async_fire(SIGNAL_STATE_UPDATED, context=service_call.context)

    reload_helper = ReloadServiceHelper(reload_service_handler)

    async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        reload_helper.execute_service,
        schema=vol.Schema({}),
    )

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    global UPDATE_UNLISTENER
    if UPDATE_UNLISTENER:
        UPDATE_UNLISTENER()

    config = {}
    for key, value in config_entry.data.items():
        config[key] = value
    for key, value in config_entry.options.items():
        config[key] = value
    if config_entry.options:
        hass.config_entries.async_update_entry(config_entry, data=config, options={})

    UPDATE_UNLISTENER = config_entry.add_update_listener(_update_listener)

    _LOGGER.info(
        "Initializing State Automate platform on %s",
        config.get(CONF_ENTITY_ID)
        if CONF_ENTITY_ID in config
        else config.get(CONF_EVENT_TYPE),
    )
    _LOGGER.debug(config)

    hass.data[DOMAIN][config_entry.entry_id] = config

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(config_entry, component)
        )

    async_dispatcher_send(hass, SIGNAL_STATE_UPDATED)

    return True


async def _update_listener(hass, config_entry):
    """Update listener."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config: ConfigEntry):
    _LOGGER.info("Unloading state_automate")

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config.entry_id)

    return unload_ok
