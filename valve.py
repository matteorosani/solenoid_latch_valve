"""Valve platform for Solenoid latch valve."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.valve import ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import setup_output, write_output
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

_LOGGER = logging.getLogger(__package__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Called by HA after async_setup_entry in __init__.py forwards to this platform.
    Reads configuration from the config entry and creates valve entities.
    """
    polarity_lock: asyncio.Lock = hass.data[DOMAIN][entry.entry_id]["polarity_lock"]

    # Hardware ports come from entry.data (set once at setup)
    red_wire_port: int = entry.data[CONF_RED_WIRE_PORT]
    black_wire_port: int = entry.data[CONF_BLACK_WIRE_PORT]

    # Tunable settings come from entry.options (editable via the options flow)
    polarity_delay: float = entry.options.get(CONF_POLARITY_DELAY, DEFAULT_POLARITY_DELAY)
    pulse_duration: float = entry.options.get(CONF_PULSE_DURATION, DEFAULT_PULSE_DURATION)
    valves_conf: list = entry.options.get(CONF_VALVES, [])

    setup_output(red_wire_port)
    setup_output(black_wire_port)

    entities = [
        PersistentRPiGPIOValve(
            name=valve[CONF_VALVE_NAME],
            port=valve[CONF_VALVE_PORT],
            red_wire_port=red_wire_port,
            black_wire_port=black_wire_port,
            polarity_lock=polarity_lock,
            polarity_delay=polarity_delay,
            pulse_duration=pulse_duration,
            # Unique ID is stable: tied to the entry + hardware port
            unique_id=f"{entry.entry_id}_port_{valve[CONF_VALVE_PORT]}",
        )
        for valve in valves_conf
    ]

    async_add_entities(entities, True)


class RPiGPIOValve(ValveEntity):
    """Representation of a latching solenoid valve on Raspberry Pi GPIO."""

    _attr_supported_features = ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE
    _attr_reports_position = False

    def __init__(
        self,
        name: str,
        port: int,
        red_wire_port: int,
        black_wire_port: int,
        polarity_lock: asyncio.Lock,
        polarity_delay: float,
        pulse_duration: float,
        unique_id: str | None = None,
    ) -> None:
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_should_poll = False
        self._port = port
        self._red_wire_port = red_wire_port
        self._black_wire_port = black_wire_port
        self._polarity_lock = polarity_lock
        self._polarity_delay = polarity_delay
        self._pulse_duration = pulse_duration
        self._state = False
        setup_output(self._port)
        write_output(self._port, 1)

    async def _pulse(self) -> None:
        """Send a brief impulse to the valve relay."""
        write_output(self._port, 0)
        await asyncio.sleep(self._pulse_duration)
        write_output(self._port, 1)

    @property
    def is_closed(self) -> bool:
        return not self._state

    async def async_open_valve(self, **kwargs: Any) -> None:
        _LOGGER.info("Opening %s", self._attr_name)
        async with self._polarity_lock:
            write_output(self._red_wire_port, 0)
            write_output(self._black_wire_port, 1)
            await asyncio.sleep(self._polarity_delay)
            await self._pulse()
            self._state = True
        self.async_write_ha_state()

    async def async_close_valve(self, **kwargs: Any) -> None:
        _LOGGER.info("Closing %s", self._attr_name)
        async with self._polarity_lock:
            write_output(self._red_wire_port, 1)
            write_output(self._black_wire_port, 0)
            await asyncio.sleep(self._polarity_delay)
            await self._pulse()
            self._state = False
        self.async_write_ha_state()


class PersistentRPiGPIOValve(RestoreEntity, RPiGPIOValve):
    """Valve that restores its state after HA restarts."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        _LOGGER.debug("Restoring state '%s' for %s", state.state, self._attr_name)
        self._state = state.state == STATE_OPEN
        if self._state:
            await self.async_open_valve()
        else:
            await self.async_close_valve()