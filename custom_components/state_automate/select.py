from __future__ import annotations
import logging
import re
from homeassistant.helpers.reload import async_setup_reload_service

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, CONF_EVENT_DATA, DEVICE_DEFAULT_NAME
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.script import Script
from homeassistant.helpers.event import async_track_state_change

from custom_components.state_automate.common import check_dict_is_contained_in_another, extract_state_from_event

from .const import CONF_ACTIVITIES, CONF_EVENT_TYPE, CONF_EVENT_VALUE, CONF_STATES, DOMAIN, KEY_ENTER, KEY_LEAVE, PLATFORMS

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
                current_option="idle",
                config=discovery_info
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
    config = hass.data[DOMAIN][config_entry.entry_id]
    await async_setup_platform(hass, {}, async_add_entities, config)


class StateAutomateSelect(SelectEntity):
    """Representation of a demo select entity."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        config: dict,
        current_option: str | None,
    ) -> None:
        """Initialize the State Automate select entity."""
        self._hass = hass
        self._config = config
        self._attr_current_option = current_option
        self._attr_icon = "mdi:remote"

        activities = config[CONF_ACTIVITIES]
        _LOGGER.debug(activities)

        self._attr_options =  [o['name'] for o in activities] 

        pattern = re.compile(fr"^{CONF_STATES}(| .+)$")
        self._activity_dict = {}
        for act in activities:
            self._activity_dict[act['name']] = {}
            for key in [key for key in act.keys() if pattern.match(key)]:
                self._activity_dict[act['name']].update(act[key])

        self._action_dict = {}

        async def _state_publisher(entity_id: str, old_state: State, new_state: State):
            _LOGGER.debug(f"New entity state {new_state.state}")
            if new_state is None:
                return      
            if str(new_state.state) not in self._action_dict:
                return

            await self._action_dict[str(new_state.state)].async_run(context=self._context)

        async def _event_publisher(event: Event):
            """Update state when event is received."""
            if check_dict_is_contained_in_another(self._event_data, event.data):
                # Extract new state
                new_state = extract_state_from_event(self._event_value, event.data)

                # Apply custom state mapping
                # if new_state in self._state_map:
                #     new_state = self._state_map[new_state]

                _LOGGER.debug(f"New event state {new_state}")
                if str(new_state) not in self._action_dict:
                    return

                await self._action_dict[str(new_state)].async_run(context=self._context)

        self._event_listener = None
        if CONF_ENTITY_ID in config:
            self._attr_unique_id = f'{DOMAIN}_{config[CONF_ENTITY_ID]}_select'
            self._attr_name = f'State Automate {config[CONF_ENTITY_ID]}'
            async_track_state_change(hass, config[CONF_ENTITY_ID], _state_publisher)
        else:
            self._attr_unique_id = f'{DOMAIN}_{config[CONF_EVENT_TYPE]}_{config[CONF_EVENT_VALUE]}_select'
            self._attr_name = f'State Automate {config[CONF_EVENT_TYPE]}'
            self._event_data = config[CONF_EVENT_DATA]
            self._event_value = config[CONF_EVENT_VALUE]
            self._event_listener = self._hass.bus.async_listen(config[CONF_EVENT_TYPE], _event_publisher)

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

    async def async_added_to_hass(self) -> None:
        if self._attr_current_option in self._activity_dict:
            for k, v in self._activity_dict[self._attr_current_option].items():
                try:
                    script_data = SCRIPT_SCHEMA(v)
                except vol.Invalid as err:
                    _LOGGER.error(err)
                    return
                script_obj = Script(self._hass, script_data, f"{DOMAIN} script", DOMAIN)
                self._action_dict[str(k)] = script_obj

    async def async_will_remove_from_hass(self):
        """Remove listeners when removing entity from Home Assistant."""
        if self._event_listener is not None:
            self._event_listener()
            self._event_listener = None
            _LOGGER.debug("%s: Removed event listener", self.entity_id)
