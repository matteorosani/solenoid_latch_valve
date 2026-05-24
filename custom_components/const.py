"""Constants for the Solenoid latch valve integration."""

DOMAIN = "solenoid_latch_valve"

# --- entry.data (hardware, not editable after setup) ---
CONF_RED_WIRE_PORT = "red_wire_port"
CONF_BLACK_WIRE_PORT = "black_wire_port"

# --- entry.options (editable via options flows) ---
CONF_POLARITY_DELAY = "polarity_delay"
CONF_PULSE_DURATION = "pulse_duration"
CONF_VALVES = "valves"
CONF_VALVE_NAME = "name"
CONF_VALVE_PORT = "port"

# --- defaults ---
DEFAULT_POLARITY_DELAY = 0.5
DEFAULT_PULSE_DURATION = 0.2