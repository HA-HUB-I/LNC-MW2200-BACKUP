# LNC MW2200A – Modbus TCP Web Interface

A lightweight **Python / Flask** web dashboard that communicates with the
LNC MW2200A CNC controller over its built-in **Modbus TCP** server (port 502).

It displays real-time machine status, axis positions, spindle/feed data and
lot/production counters, and lets operators issue commands from any browser on
the local network.

---

## Features

| Feature | Description |
|---|---|
| **Status** | Machine state flags (E-Stop, Alarm, Cycle, Feed Hold, Homing, Spindle, Pause, Door) |
| **Positions** | Live X / Y / Z axis positions in mm (0.001 mm resolution) |
| **Spindle & Feed** | Spindle RPM and feed rate with visual gauges |
| **Lot tracking** | Parts count vs. target, lot ID, progress bar, set target, reset counter |
| **Controls** | Cycle Start, Feed Hold, Reset/Clear Alarm, Spindle CW/CCW, Coolant, E-Stop |
| **Auto-reconnect** | Background poller reconnects automatically if the connection is lost |

## Prerequisites

- Python 3.9 or later
- The LNC controller's **Modbus TCP server enabled** (parameter `45010 = 1`,
  port 502 – see `Eth_ModbusServerTCP.ini`)

## Installation

```bash
cd modbus_web
pip install -r requirements.txt
```

## Configuration

All settings can be overridden with **environment variables**:

| Variable | Default | Description |
|---|---|---|
| `MODBUS_HOST` | `192.168.1.100` | IP address of the LNC controller |
| `MODBUS_PORT` | `502` | Modbus TCP port |
| `MODBUS_UNIT` | `1` | Modbus device/unit ID |
| `POLL_INTERVAL` | `0.5` | Polling interval in seconds |
| `WEB_HOST` | `0.0.0.0` | Web server bind address |
| `WEB_PORT` | `5000` | Web server port |
| `WEB_DEBUG` | `false` | Enable Flask debug mode |

## Running

```bash
# With defaults (controller at 192.168.1.100:502)
python app.py

# Custom controller IP
MODBUS_HOST=192.168.0.50 python app.py

# Custom port, debug mode
MODBUS_HOST=10.0.0.10 WEB_PORT=8080 WEB_DEBUG=true python app.py
```

Then open **http://localhost:5000** (or the server's IP) in a browser.

## API Endpoints

### `GET /api/status`
Returns the current machine state as JSON.

```json
{
  "connected": true,
  "x_pos": 125.345,
  "y_pos": -50.012,
  "z_pos": 0.000,
  "spindle_rpm": 8000,
  "feed_rate": 3000,
  "alarm_code": 0,
  "program_number": 1001,
  "lot_count": 47,
  "lot_target": 100,
  "lot_id": 5,
  "lot_progress_pct": 47.0,
  "cycle_running": true,
  "estop_active": false,
  "alarm_active": false,
  ...
}
```

### `POST /api/command`
Issue a machine command by writing a coil.

```json
{ "command": "cycle_start", "value": true }
```

Available commands:

| Command | Description |
|---|---|
| `cycle_start` | Start machining cycle |
| `feed_hold` | Pause feed (Feed Hold) |
| `reset` | Reset / clear active alarm |
| `spindle_cw` | Spindle clockwise |
| `spindle_ccw` | Spindle counter-clockwise |
| `coolant` | Toggle coolant |
| `estop` | Software Emergency Stop |
| `lot_reset` | Reset lot counter to 0 |

### `POST /api/lot/set_target`
Set a new lot target quantity.

```json
{ "target": 200 }
```

## Modbus Register Map

The application reads **holding registers** (function code 3) starting at
address 0. Register numbers below are **0-based** (Modbus PDU addressing).

| Address | Description | Unit |
|---|---|---|
| 0 | Machine status word (bit flags) | — |
| 1–2 | X position (signed 32-bit, lo/hi words) | × 0.001 mm |
| 3–4 | Y position | × 0.001 mm |
| 5–6 | Z position | × 0.001 mm |
| 7 | Spindle speed | RPM |
| 8 | Feed rate | mm/min |
| 9 | Active alarm code | — |
| 10 | Program number | — |
| 11 | Lot count (parts produced) | — |
| 12 | Lot target | — |
| 13 | Lot ID | — |
| 5000 | Connection status (`OpenPortResultAddr`) | — |

### Status Word Bit Map

| Bit | Meaning |
|---|---|
| 0 | Emergency Stop active |
| 1 | Alarm active |
| 2 | Cycle running |
| 3 | Feed Hold active |
| 4 | Homing in progress |
| 5 | Spindle running |
| 6 | Program paused |
| 7 | Door open |

> **Note**: The exact register assignments depend on the PLC program loaded on
> the LNC controller. Adjust the register constants at the top of `app.py` to
> match your specific machine's Modbus mapping.

## Enabling Modbus TCP on the LNC Controller

On the machine HMI, set the following parameters:

| Parameter | Value | Description |
|---|---|---|
| `45010` | `1` | Enable Modbus Server TCP |
| `45011` | `0` | Disable Modbus Client TCP (unless needed) |

The default TCP port is **502** (configurable in `Eth_ModbusServerTCP.ini`).

## Security Notice

This application is intended for use on a **trusted local network** only.
It does not include authentication or TLS. Do not expose it to the public
internet.

> **Authentication**: Modbus TCP has **no built-in authentication**. Any client
> that can reach port 502 on the LNC controller can read/write registers. Ensure
> the controller is on an isolated machine network or protected by a firewall.

## Troubleshooting / Diagnostics

If the dashboard shows **Disconnected**, check the following:

1. **Verify Modbus TCP is enabled** on the LNC controller:
   - Set parameter `45010 = 1` via the HMI.
   - The default port is **502** (configurable in `Eth_ModbusServerTCP.ini`).

2. **Check network reachability** – ping the controller IP and confirm port 502 is open:
   ```bash
   ping <controller-ip>
   # from Linux:
   nc -zv <controller-ip> 502
   ```

3. **Inspect the live error message** – the dashboard now shows the last Modbus
   error directly under the connection badge when disconnected.

4. **Use the Scan endpoint** to read raw register values and verify the endpoint
   mapping without relying on the polling thread:
   ```bash
   curl http://localhost:5000/api/scan
   ```

5. **Use the Diagnostics endpoint** for a full summary of the configuration,
   register/coil map, and connection state:
   ```bash
   curl http://localhost:5000/api/diagnostics
   ```

6. **Unit ID (Slave ID)** – the default is `1`. If your controller uses a
   different slave ID, set `MODBUS_UNIT=<id>` before starting the app.

7. **Register addresses are 0-based** (Modbus PDU). Some Modbus tools show
   1-based Modicon-style addresses — for holding registers, 0-based address 0
   becomes 40001 in Modicon notation (40000 + address + 1).

### New API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/diagnostics` | GET | Config, register map, last error, connection hints |
| `/api/scan` | GET | Fresh Modbus read of all mapped registers and coils with raw values |
