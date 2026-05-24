"""The Solenoid latch valve integration."""

from __future__ import annotations

import asyncio
import logging

try:
    from RPi import GPIO
except ImportError:
    from . import gpio_stub as GPIO

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN

_LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.VALVE]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Called once when the domain loads.
    With config entries we don't do much here — just ensure our
    hass.data bucket exists.
    """
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Called when a config entry is loaded (on HA start, or after being added).
    This is where we initialise hardware and forward setup to the valve platform.
    """
    hass.data.setdefault(DOMAIN, {})

    GPIO.setmode(GPIO.BCM)
    _LOGGER.debug("GPIO mode set to BCM")

    # Store per-entry data (the lock is shared across all valves in this entry)
    hass.data[DOMAIN][entry.entry_id] = {
        "polarity_lock": asyncio.Lock(),
    }

    # Forward setup to the valve platform — this calls async_setup_entry in valve.py
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register a listener: when options change, reload the entry so
    # entities are recreated with the new configuration
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Called when a config entry is removed or HA is stopping.
    We must undo everything done in async_setup_entry.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        GPIO.cleanup()
        _LOGGER.debug("GPIO cleaned up")

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Called by the update listener when options change.
    A full reload recreates all entities with the updated configuration.
    """
    _LOGGER.debug("Reloading entry due to options change")
    await hass.config_entries.async_reload(entry.entry_id)


def setup_output(port: int) -> None:
    """Set up a GPIO pin as output."""
    GPIO.setup(port, GPIO.OUT)


def write_output(port: int, value: int) -> None:
    """Write a value to a GPIO pin."""
    GPIO.output(port, value)