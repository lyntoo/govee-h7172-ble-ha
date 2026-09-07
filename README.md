<img width="1547" height="628" alt="Screenshot from 2026-09-07 09-52-12" src="https://github.com/user-attachments/assets/11ef43ab-807d-4556-a451-80a4d4796976" />
# Govee H7172 Ice Maker (BLE) for Home Assistant

A custom Home Assistant integration for the **Govee H7172** portable ice maker, controlled entirely over **Bluetooth LE** — no cloud, no Wi-Fi, no Govee account required.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=lyntoo&repository=govee-h7172-ble-ha&category=integration)

---

## Why

The Govee H7172 only exposes basic on/off and work-mode state through Govee's cloud REST API and MQTT broker — critically, it **never reports alarm conditions** (e.g. low water) through the cloud at all. The only way to get real-time status, including alarms, is a direct local BLE connection to the device. This integration talks to it directly, with zero dependency on Govee's servers.

The full BLE protocol (service/characteristic UUIDs, packet format, command bytes) was reverse-engineered from the official Govee Home Android app.

---

## Features

- **Fully local** — BLE only, no Govee account, no internet dependency, no open ports
- **Automatic discovery** — devices advertising the Govee service UUID show up for one-tap setup; manual BLE address entry also supported
- **Live state via BLE notifications** — no polling loop required for state changes
- **Entities:**
  - `sensor` — work status (idle / making ice / ice ready / washing / wash complete / scheduled), ice size mode (large / medium / small), raw alarm code (diagnostic, disabled by default)
  - `binary_sensor` — power, alarm (low water), ice tray full

---

## Requirements

- Home Assistant Core with the built-in `bluetooth` integration enabled
- A Bluetooth adapter (or ESPHome Bluetooth proxy) within range of the ice maker
- Python packages `bleak>=0.21.1` and `bleak-retry-connector>=3.0.0` (installed automatically by Home Assistant)

---

## Installation

### Via HACS (custom repository)

1. Click the badge above, or go to **HACS → Integrations → ⋮ → Custom repositories**
2. Add `https://github.com/lyntoo/govee-h7172-ble-ha` as an **Integration**
3. Search for **Govee H7172 Ice Maker (BLE)** and install
4. Restart Home Assistant

### Manual

1. Copy the `custom_components/govee_h7172_ble` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Power on the ice maker and make sure it's within Bluetooth range of your Home Assistant host or a Bluetooth proxy
2. Home Assistant should auto-discover it — go to **Settings → Devices & services** and confirm the discovered device
3. If it isn't auto-discovered, go to **Settings → Devices & services → Add Integration**, search for **Govee H7172**, and enter the Bluetooth address manually

---

## Uninstalling

**Settings → Devices & services → Govee H7172 → ⋮ → Delete**, then remove the `custom_components/govee_h7172_ble` folder (or remove it via HACS). No credentials or accounts were ever stored — the config entry only holds the device's Bluetooth address.

---

## Protocol notes

Packets are 20 bytes, zero-padded, with a `0x33` header for app→device writes and `0xAA` for device→app notifications. Confirmed commands cover work-status query, mode query, alarm query, and switch state (power / ice-full) — see the source for exact byte layouts. Passive BLE advertising also exposes power state and work status without an active connection (manufacturer ID `0xEC88`).

---

## Disclaimer

This project is not affiliated with or endorsed by Govee. It was built by reverse-engineering the official Govee Home Android app's Bluetooth protocol for personal, local use. Use at your own risk.
