"""Config flow for Solenoid latch valve."""

from __future__ import annotations
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_BLACK_WIRE_PORT,
    CONF_POLARITY_DELAY,
    CONF_PULSE_DURATION,
    CONF_RED_WIRE_PORT,
    CONF_VALVE_NAME,
    CONF_VALVE_PORT,
    CONF_VALVES,
    DEFAULT_POLARITY_DELAY,
    DEFAULT_PULSE_DURATION,
    DOMAIN,
)


class SolenoidLatchValveConfigFlow(ConfigFlow, domain=DOMAIN):
    """
    Handles the initial setup flow shown when you click 'Add Integration'.

    VERSION is important: if you change the data structure in a future update,
    increment this and add a migration method so existing installs don't break.
    """

    VERSION = 1

    def __init__(self) -> None:
        self._controller_data: dict = {}  # accumulates data across steps
        self._valves: list = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """
        Step 1: collect hardware ports and timing defaults.
        'async_step_user' is always the entry point when a user adds an integration.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Basic validation: the two polarity ports must be different
            if user_input[CONF_RED_WIRE_PORT] == user_input[CONF_BLACK_WIRE_PORT]:
                errors["base"] = "duplicate_polarity_ports"
            else:
                self._controller_data = user_input
                # Proceed to valve setup
                return await self.async_step_add_valve()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RED_WIRE_PORT): cv.positive_int,
                    vol.Required(CONF_BLACK_WIRE_PORT): cv.positive_int,
                    vol.Optional(
                        CONF_POLARITY_DELAY, default=DEFAULT_POLARITY_DELAY
                    ): vol.Coerce(float),
                    vol.Optional(
                        CONF_PULSE_DURATION, default=DEFAULT_PULSE_DURATION
                    ): vol.Coerce(float),
                }
            ),
            errors=errors,
        )

    async def async_step_add_valve(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """
        Step 2: add at least one valve.
        The 'add_another' boolean lets the user loop back to add more.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_VALVE_PORT]

            # Validate: port must not clash with polarity ports or existing valves
            reserved = {
                self._controller_data[CONF_RED_WIRE_PORT],
                self._controller_data[CONF_BLACK_WIRE_PORT],
            }
            existing_ports = {v[CONF_VALVE_PORT] for v in self._valves}

            if port in reserved:
                errors[CONF_VALVE_PORT] = "port_reserved_for_polarity"
            elif port in existing_ports:
                errors[CONF_VALVE_PORT] = "duplicate_valve_port"
            else:
                self._valves.append(
                    {
                        CONF_VALVE_NAME: user_input[CONF_VALVE_NAME],
                        CONF_VALVE_PORT: port,
                    }
                )
                if user_input.get("add_another"):
                    # Loop back to this same step
                    return await self.async_step_add_valve()
                else:
                    # All done — create the config entry
                    # Note the data/options split:
                    #   data    = hardware (ports), not editable later
                    #   options = everything tunable (timing, valves)
                    return self.async_create_entry(
                        title="Irrigation Controller",
                        data={
                            CONF_RED_WIRE_PORT: self._controller_data[CONF_RED_WIRE_PORT],
                            CONF_BLACK_WIRE_PORT: self._controller_data[CONF_BLACK_WIRE_PORT],
                        },
                        options={
                            CONF_POLARITY_DELAY: self._controller_data[CONF_POLARITY_DELAY],
                            CONF_PULSE_DURATION: self._controller_data[CONF_PULSE_DURATION],
                            CONF_VALVES: self._valves,
                        },
                    )

        # Show how many valves have been added so far in the description
        valve_count = len(self._valves)
        description = (
            f"{valve_count} valve(s) added so far."
            if valve_count > 0
            else "Add at least one valve."
        )

        return self.async_show_form(
            step_id="add_valve",
            description_placeholders={"valve_count": description},
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VALVE_NAME): cv.string,
                    vol.Required(CONF_VALVE_PORT): cv.positive_int,
                    vol.Optional("add_another", default=False): bool,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SolenoidLatchValveOptionsFlow:
        """
        Tell HA that this integration has an options flow.
        The gear icon will appear on the integration card.
        """
        return SolenoidLatchValveOptionsFlow()


class SolenoidLatchValveOptionsFlow(OptionsFlow):
    """
    Options flow: reached via the gear icon after the integration is set up.
    Lets the user edit timing and manage valves without re-adding the integration.
    """

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """
        Show a menu so the user can choose what to edit.
        async_show_menu renders a list of choices, each mapping to a step method.
        """
        return self.async_show_menu(
            step_id="init",
            menu_options=["edit_timing", "add_valve", "remove_valve"],
        )

    async def async_step_edit_timing(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit polarity delay and pulse duration."""
        if user_input is not None:
            # Merge updated timing into existing options (preserve valves)
            return self.async_create_entry(
                data={**self.config_entry.options, **user_input}
            )

        return self.async_show_form(
            step_id="edit_timing",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_POLARITY_DELAY,
                        default=self.config_entry.options.get(
                            CONF_POLARITY_DELAY, DEFAULT_POLARITY_DELAY
                        ),
                    ): vol.Coerce(float),
                    vol.Optional(
                        CONF_PULSE_DURATION,
                        default=self.config_entry.options.get(
                            CONF_PULSE_DURATION, DEFAULT_PULSE_DURATION
                        ),
                    ): vol.Coerce(float),
                }
            ),
        )

    async def async_step_add_valve(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a new valve."""
        errors: dict[str, str] = {}

        if user_input is not None:
            port = user_input[CONF_VALVE_PORT]
            reserved = {
                self.config_entry.data[CONF_RED_WIRE_PORT],
                self.config_entry.data[CONF_BLACK_WIRE_PORT],
            }
            current_valves = list(self.config_entry.options.get(CONF_VALVES, []))
            existing_ports = {v[CONF_VALVE_PORT] for v in current_valves}

            if port in reserved:
                errors[CONF_VALVE_PORT] = "port_reserved_for_polarity"
            elif port in existing_ports:
                errors[CONF_VALVE_PORT] = "duplicate_valve_port"
            else:
                current_valves.append(
                    {
                        CONF_VALVE_NAME: user_input[CONF_VALVE_NAME],
                        CONF_VALVE_PORT: port,
                    }
                )
                return self.async_create_entry(
                    data={**self.config_entry.options, CONF_VALVES: current_valves}
                )

        return self.async_show_form(
            step_id="add_valve",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VALVE_NAME): cv.string,
                    vol.Required(CONF_VALVE_PORT): cv.positive_int,
                }
            ),
            errors=errors,
        )

    async def async_step_remove_valve(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Remove an existing valve."""
        current_valves = self.config_entry.options.get(CONF_VALVES, [])

        if user_input is not None:
            selected_port = int(user_input["valve"])
            new_valves = [
                v for v in current_valves if v[CONF_VALVE_PORT] != selected_port
            ]
            return self.async_create_entry(
                data={**self.config_entry.options, CONF_VALVES: new_valves}
            )

        # Build a port→name map for the selector
        valve_options = {
            str(v[CONF_VALVE_PORT]): v[CONF_VALVE_NAME] for v in current_valves
        }

        return self.async_show_form(
            step_id="remove_valve",
            data_schema=vol.Schema(
                {vol.Required("valve"): vol.In(valve_options)}
            ),
        )