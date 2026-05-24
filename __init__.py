"""The Solenoid latch valve integration."""

from __future__ import annotations

import logging

from RPi import GPIO  # pylint: disable=import-error

from homeassistant.const import (
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__package__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


def setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Raspberry PI GPIO component."""

    def cleanup_gpio(event):
        """Stuff to do before stopping."""
        _LOGGER.debug("Cleanup GPIO")
        GPIO.cleanup()

    def prepare_gpio(event):
        """Stuff to do when Home Assistant starts."""
        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, cleanup_gpio)

    _LOGGER.debug("Setup events")
    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, prepare_gpio)
    GPIO.setmode(GPIO.BCM)
    _LOGGER.debug("Setup completed")
    return True


def setup_output(port):
    """Set up a GPIO as output."""
    GPIO.setup(port, GPIO.OUT)


def write_output(port, value):
    """Write a value to a GPIO."""
    GPIO.output(port, value)
