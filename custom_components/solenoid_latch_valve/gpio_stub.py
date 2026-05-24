"""Stub for RPi.GPIO for development on non-Raspberry Pi systems."""

BCM = "BCM"
OUT = "OUT"


def setmode(mode):
    pass


def setup(port, mode):
    pass


def output(port, value):
    pass


def cleanup():
    pass