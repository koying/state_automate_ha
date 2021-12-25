from __future__ import annotations
import logging
from homeassistant.helpers.reload import async_setup_reload_service

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, DEVICE_DEFAULT_NAME
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.script import Script
from homeassistant.helpers.event import async_track_state_change

from .const import CONF_ACTIVITIES, DOMAIN, KEY_ENTER, KEY_LEAVE, PLATFORMS

SCRIPT_SCHEMA = vol.Schema(cv.SCRIPT_SCHEMA)

_LOGGER = logging.getLogger(__name__)

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up the Select entity."""
    async_add_entities(
        [
            StateAutomateSelect(
                hass,
                unique_id=f'{DOMAIN}_{discovery_info[CONF_ENTITY_ID]}_select',
                entity_id=discovery_info[CONF_ENTITY_ID],
                name=f'State Automate {discovery_info[CONF_ENTITY_ID]}',
                icon="mdi:remote",
                current_option="none",
                activities=discovery_info[CONF_ACTIVITIES],
            ),
        ]
    )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the StateAutomate config entry."""
    if config_entry.entry_id not in hass.data[DOMAIN]:
        return
    activities = hass.data[DOMAIN][config_entry.entry_id][config_entry.data.get(CONF_ENTITY_ID)]
    await async_setup_platform(hass, {}, async_add_entities, {CONF_ENTITY_ID: config_entry.data.get(CONF_ENTITY_ID), CONF_ACTIVITIES: activities})


class StateAutomateSelect(SelectEntity):
    """Representation of a demo select entity."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        unique_id: str,
        entity_id: str,
        name: str,
        icon: str,
        current_option: str | None,
        activities: list,
    ) -> None:
        """Initialize the Demo select entity."""
        self._hass = hass
        self._attr_unique_id = unique_id
        self._attr_name = name or DEVICE_DEFAULT_NAME
        self._attr_current_option = current_option
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, unique_id)},
            name=name,
        )
        _LOGGER.debug(activities)

        self._attr_options =  [o['name'] for o in activities] 

        self._entity_id = entity_id
        self._activity_dict = {}
        for act in activities:
            self._activity_dict[act['name']] = act['states']
        self._action_dict = {}

        async def _state_publisher(entity_id: str, old_state: State, new_state: State):
            _LOGGER.debug(f"New state {new_state.state}")
            if new_state is None:
                return      
            if new_state.state not in self._action_dict:
                return

            await self._action_dict[new_state.state].async_run(context=self._context)

        async_track_state_change(hass, self._entity_id, _state_publisher)

    async def async_select_option(self, option: str) -> None:
        """Update the current selected option."""

        if option == self._attr_current_option:
            return

        if KEY_LEAVE in self._action_dict:
            await self._action_dict[KEY_LEAVE].async_run(context=self._context)

        self._attr_current_option = option
        self._action_dict = {}
        for k, v in self._activity_dict[self._attr_current_option].items():
            try:
                script_data = SCRIPT_SCHEMA(v)
            except vol.Invalid as err:
                _LOGGER.error(err)
                return
            script_obj = Script(self._hass, script_data, f"{DOMAIN} script", DOMAIN)
            self._action_dict[str(k)] = script_obj

        if KEY_ENTER in self._action_dict:
            await self._action_dict[KEY_ENTER].async_run(context=self._context)

        _LOGGER.debug(self._action_dict)

        self.async_write_ha_state()
