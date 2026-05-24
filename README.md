# Solenoid Latch Valve — Home Assistant Custom Integration

A custom [Home Assistant](https://www.home-assistant.io/) integration for controlling **latching solenoid valves** via Raspberry Pi GPIO, designed for irrigation systems.

Latching solenoids require a brief electrical impulse to open and a reverse-polarity impulse to close. This integration manages a 4-relay H-bridge circuit transparently, exposing each valve as a simple **Valve entity** in the HA UI.

---

## How it works

The circuit uses four relays controlled by the Raspberry Pi's GPIO pins:

| Relay | Role |
|---|---|
| Relay 3 + 4 | Control polarity — switching one on and the other off determines current direction |
| Relay 1 + 2 | One per valve — send the impulse to the solenoid |

To **open** a valve: polarity is set in one direction, a short pulse is sent to the valve relay.  
To **close** a valve: polarity is inverted, a short pulse is sent again.

The integration handles all of this automatically. From the HA side, each valve is a standard open/close entity.

```
Raspberry Pi GPIO
      │
  ┌───┴────────────┐
  │  Relay 3 + 4   │  ← polarity control (shared)
  └───────┬────────┘
          │
  ┌───────┴────────┐
  │  Relay 1 + 2   │  ← one per valve
  └───────┬────────┘
          │
   Solenoid valves
```

---

## Requirements

- Raspberry Pi running Home Assistant (tested on Home Assistant OS)
- 4-relay board connected to GPIO (BCM numbering)
- 2 latching solenoid valves
- [HACS](https://hacs.xyz) for easy installation and updates

---

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations → Custom Repositories**
3. Add this repository URL and select category **Integration**
4. Click **Install**
5. Restart Home Assistant

Updates will appear automatically in HACS when a new release is published.

### Manual

1. Download or clone this repository
2. Copy the `custom_components/solenoid_latch_valve/` folder into your HA config directory:
   ```
   /config/custom_components/solenoid_latch_valve/
   ```
3. Restart Home Assistant

---

## Configuration

After installation, add the integration via the UI:

**Settings → Devices & Services → Add Integration → Solenoid Latch Valve**

The setup flow has two steps:

**Step 1 — Controller**

| Field | Description | Example |
|---|---|---|
| Red wire GPIO port | BCM pin number for polarity relay (+) | `18` |
| Black wire GPIO port | BCM pin number for polarity relay (−) | `22` |
| Polarity switch delay | Seconds to wait after setting polarity before pulsing | `0.5` |
| Pulse duration | How long the impulse lasts in seconds | `0.2` |

**Step 2 — Valves**

| Field | Description | Example |
|---|---|---|
| Valve name | Display name in HA | `Garden valve` |
| GPIO port | BCM pin number for this valve's relay | `12` |
| Add another valve | Loop back to add more | — |

### Editing settings after setup

Click the **⚙ gear icon** on the integration card to:
- Edit timing parameters
- Add a new valve
- Remove an existing valve

Changes trigger an automatic reload of the integration.

---

## State persistence

Valve states survive Home Assistant restarts. On startup, each valve is re-pulsed to match the last known state, ensuring the physical position always matches what HA shows.

---

## Development

To work on this integration outside of a Raspberry Pi, a GPIO stub is included. It silently no-ops all GPIO calls, allowing the integration to load without errors on any machine.

```bash
python -m venv .venv
source .venv/bin/activate
pip install homeassistant
```

Point your IDE to `.venv` and all Home Assistant imports will resolve correctly.

---

## License

MIT License — see [LICENSE](LICENSE) for details.