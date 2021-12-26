"""Constants for the state_automate integration."""

DOMAIN = "state_automate"
PLATFORMS = ["select"]

SIGNAL_STATE_UPDATED = "{}.updated".format(DOMAIN)

KEY_ENTER = "enter"
KEY_LEAVE = "leave"

CONF_ACTIVITIES = "activities"
CONF_STATES = "states"
CONF_EVENT_TYPE = "event_type"
CONF_EVENT_VALUE = "event_value"
