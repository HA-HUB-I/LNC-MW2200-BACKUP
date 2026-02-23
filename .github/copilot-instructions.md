# Copilot Instructions for LNC MW2200A CNC Controller Repository

## Repository Purpose

This repository is a backup of the configuration and software for an **LNC MW2200A CNC controller** used to operate a **wood CNC routing machine**. It contains:

- Machine configuration files (parameters, keymap, PLC project)
- HMI (Human-Machine Interface) layout and language string files
- PLC (Programmable Logic Controller) logic
- A Python/Flask **Modbus TCP web dashboard** (`modbus_web/`) for real-time monitoring and control

---

## Repository Structure

```
disk2/           # HMI language/string files (.str)
disk3/           # HMI layout (ohframe.xml, .png images, .str files), logs
  data/
    open_custom_bottom/   # Custom HMI bottom panel layout
    open_extend_1/        # Extended HMI panel layout
    log/                  # System and operation logs
disk4/           # Core machine configuration
  machine/
    param.txt           # Current machine parameter values
    param_define.txt    # Parameter definitions (names, types, ranges)
    cnc.lpar            # Binary parameter store
    plc.prj             # PLC project file
    keymap.ini          # Key-to-function mapping for control panel
modbus_web/      # Python/Flask Modbus TCP web interface
  app.py              # Main Flask application
  requirements.txt    # Python dependencies
  templates/          # Jinja2 HTML templates
```

---

## Technology Stack

### Machine / Controller
- **Controller**: LNC MW2200A (proprietary CNC controller)
- **Machine type**: Wood CNC router/milling machine
- **Communication**: Modbus TCP (port 502) for external monitoring and commands
- **HMI**: Proprietary XML-based layout (`ohframe.xml`) with `.str` language files
- **PLC**: Proprietary LNC PLC project (`plc.prj`) – requires LNC software to edit

### Web Dashboard (`modbus_web/`)
- **Language**: Python 3.9+
- **Framework**: Flask
- **Modbus library**: `pymodbus`
- **Communication**: Modbus TCP (holding registers + discrete coils)

---

## Key Concepts

### Modbus Register Map (0-based PDU addresses)
| Address | Description | Unit |
|---------|-------------|------|
| 0       | Machine status word (bit flags) | — |
| 1–2     | X axis position (signed 32-bit lo/hi) | × 0.001 mm |
| 3–4     | Y axis position | × 0.001 mm |
| 5–6     | Z axis position | × 0.001 mm |
| 7       | Spindle speed | RPM |
| 8       | Feed rate | mm/min |
| 9       | Active alarm code | — |
| 10      | Program number | — |
| 11      | Lot count (parts produced) | — |
| 12      | Lot target | — |
| 13      | Lot ID | — |
| 5000    | Connection status (`OpenPortResultAddr`) | — |

### Status Word Bit Map
| Bit | Meaning |
|-----|---------|
| 0   | Emergency Stop active |
| 1   | Alarm active |
| 2   | Cycle running |
| 3   | Feed Hold active |
| 4   | Homing in progress |
| 5   | Spindle running |
| 6   | Program paused |
| 7   | Door open |

### Coil Map (discrete outputs, 0-based)
| Coil | Function |
|------|----------|
| 0    | Cycle Start |
| 1    | Feed Hold |
| 2    | Reset / Clear Alarm |
| 3    | Spindle CW |
| 4    | Spindle CCW |
| 5    | Coolant ON |
| 6    | E-Stop (software) |
| 7    | Lot Reset |

### M-Code Examples (PLC macros in ohframe.xml)
| M-Code | Function |
|--------|----------|
| M10    | Vacuum Pump 1 ON |
| M11    | Vacuum Pump 1 OFF |
| M140   | Dust Cover UP |

---

## Development Guidelines

### Modifying `modbus_web/app.py`
- All Modbus register constants are defined at the top of `app.py` — update them there if the machine's Modbus mapping changes.
- The background polling thread reconnects automatically on connection loss.
- Environment variables (`MODBUS_HOST`, `MODBUS_PORT`, `MODBUS_UNIT`, `POLL_INTERVAL`, `WEB_HOST`, `WEB_PORT`, `WEB_DEBUG`) override all defaults.
- Do **not** expose the web dashboard to the public internet — it has no authentication and Modbus TCP has no built-in security.

### Running the Web Dashboard
```bash
cd modbus_web
pip install -r requirements.txt
MODBUS_HOST=<controller-ip> python app.py
# Open http://localhost:5000
```

### Modifying Machine Configuration Files
- **`disk4/machine/param.txt`**: Human-readable parameter values. Load onto the controller via HMI File Management after editing.
- **`disk3/data/open_custom_bottom/ohframe.xml`**: HMI custom bottom panel. Add `<Macro>` entries in `<MacroList>` and `<QohButton>` elements for new buttons.
- **Always back up** configuration files before making changes.
- **Caution**: Incorrect parameter or PLC changes can cause machine malfunction.

### Enabling Modbus TCP on the Controller
Set via machine HMI parameters:
- `45010 = 1` → Enable Modbus Server TCP
- `45011 = 0` → Disable Modbus Client TCP (unless needed)

---

## Safety Warnings

- This is a **real industrial machine**. Incorrect software changes can cause physical damage or injury.
- Always test changes in a safe, controlled environment.
- Never send E-Stop or spindle commands unless the operator is aware and the machine is in a safe state.
- The Modbus TCP interface provides no authentication — keep it on an isolated machine network or behind a firewall.
