"""Allows to configure a valve using RPi GPIO."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import (
    CONF_NAME,
    CONF_PORT,
    CONF_SWITCHES,
    CONF_UNIQUE_ID,
    DEVICE_DEFAULT_NAME,
    STATE_ON,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.reload import setup_reload_service
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from . import PLATFORMS, setup_output, write_output
from .const import CONF_BLACK_WIRE_PORT, CONF_RED_WIRE_PORT, DOMAIN

_LOGGER = logging.getLogger(__package__)

_VALVE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_PORT): cv.positive_int,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_SWITCHES): vol.All(cv.ensure_list, [_VALVE_SCHEMA]),
        vol.Required(CONF_RED_WIRE_PORT): cv.positive_int,
        vol.Required(CONF_BLACK_WIRE_PORT): cv.positive_int,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Raspberry PI GPIO devices."""
    setup_reload_service(hass, DOMAIN, PLATFORMS)

    hass.data.setdefault(DOMAIN, {})
    if "polarity_lock" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["polarity_lock"] = asyncio.Lock()

    polarity_lock = hass.data[DOMAIN]["polarity_lock"]

    _LOGGER.debug("Loading switch platform with config %s", config)

    valves_conf: list | None = config.get(CONF_SWITCHES)
    red_wire_port = config[CONF_RED_WIRE_PORT]
    black_wire_port = config[CONF_BLACK_WIRE_PORT]

    if valves_conf is None:
        return

    setup_output(red_wire_port)
    setup_output(black_wire_port)

    valves = [
        PersistentRPiGPIOValve(
            valve[CONF_NAME],
            valve[CONF_PORT],
            red_wire_port,
            black_wire_port,
            polarity_lock,
            valve.get(CONF_UNIQUE_ID),
        )
        for valve in valves_conf
    ]

    add_entities(valves, True)


class RPiGPIOValve(SwitchEntity):
    """Representation of a Raspberry Pi GPIO."""

    def __init__(
        self,
        name,
        port,
        red_wire_port,
        black_wire_port,
        polarity_lock: asyncio.Lock,
        unique_id=None,
    ) -> None:
        """Initialize the pin."""
        self._attr_name = name or DEVICE_DEFAULT_NAME
        self._attr_unique_id = unique_id
        self._attr_should_poll = False
        self._port = port
        self._red_wire_port = red_wire_port
        self._black_wire_port = black_wire_port
        self._polarity_lock = polarity_lock
        self._state = False
        setup_output(self._port)
        write_output(self._port, 1)

    async def _pulse(self):
        write_output(self._port, 0)
        await asyncio.sleep(0.2)
        write_output(self._port, 1)

    @property
    def is_on(self) -> bool | None:
        """Return true if the valve is open."""
        return self._state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Open the valve."""
        _LOGGER.info("Turn on %s", self._attr_name)
        async with self._polarity_lock:
            write_output(self._red_wire_port, 0)
            write_output(self._black_wire_port, 1)
            await asyncio.sleep(0.5)
            await self._pulse()
            self._state = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close the valve."""
        _LOGGER.info("Turn off %s", self._attr_name)
        async with self._polarity_lock:
            write_output(self._red_wire_port, 1)
            write_output(self._black_wire_port, 0)
            await asyncio.sleep(0.5)
            await self._pulse()
            self._state = False
        self.async_write_ha_state()


class PersistentRPiGPIOValve(RPiGPIOValve, RestoreEntity):
    """Representation of a persistent Raspberry Pi GPIO."""

    def __init__(
        self, name, port, red_wire_port, black_wire_port, polarity_lock, unique_id=None
    ) -> None:
        """Initialize the pin."""
        super().__init__(name, port, red_wire_port, black_wire_port, polarity_lock, unique_id)

    async def async_added_to_hass(self) -> None:
        """Call when the switch is added to hass."""
        _LOGGER.debug("Added to HASS called for %s", self._attr_name)
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if not state:
            return
        self._state = state.state == STATE_ON
        if self._state:
            await self.async_turn_on()
        else:
            await self.async_turn_off()
