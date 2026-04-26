---
name: lnc-modbus-expert
description: >-
  Provides verified Modbus TCP register maps, polling strategies, and architectural rules for developing the LNC MW2200A CNC Dashboard. Use this when adding new features, troubleshooting real-time data collection, or modifying the Flask backend.
---

# LNC MW2200A Modbus Expert

This skill encapsulates the verified knowledge required to safely and correctly read real-time data from the LNC MW2200A CNC controller via Modbus TCP.

## Core Mandates

1. **Do not guess registers**: The machine map is highly irregular due to `RegisterMode=-32`. Use only the verified registers listed below. If new data is needed, use the scripts in `modbus_web/discovery/` to find it safely while the machine is running.
2. **Modular Architecture**: The backend MUST remain split into `models.py`, `config.py`, `modbus_worker.py`, and `app.py`. Do not create monolithic scripts. The UI MUST remain split into `index.html`, `style.css`, and `app.js`.
3. **Unit ID**: The `MODBUS_UNIT` must be `1`. Unit 0 works for some registers but fails to provide critical diagnostic data (e.g., G-Code line).
4. **Block Reads**: Never read registers one-by-one. Use `read_holding_registers` with `count=50` or `100` to fetch entire zones (e.g., 11500-11650, 12000-12100) and extract data via list indices.

## Verified Register Map

See [modbus_map.md](references/modbus_map.md) for the full detailed log.

### Axis Coordinates (Scale: 0.001 mm)

*Note: The physical axes on this machine are swapped in Modbus relative to standard LNC defaults to match the display.*

*   **Machine X (Relative):** `R11570` (Int16)
*   **Machine Y (Relative):** `R11565` (Int16)
*   **Machine Z (Relative):** `R11560` (Int16)
*   **Absolute X (Work G54):** `R12032` (Int16)
*   **Absolute Y (Work G54):** `R12038` (Int16)
*   **Absolute Z (Work G54):** `R12034` (Int16)

### Speeds

*   **Feed Rate (Actual):** `R11638` (Int16, mm/min)
*   **Spindle RPM:** `R1007` (Int16)
*   **Feed Override:** `R8067` (Divide by 10 for percentage)
*   **Spindle Override:** `R8069` (Divide by 10 for percentage)

### Status & Control

*   **Status Word (R0)**:
    *   Bit 0: E-Stop Active
    *   Bit 1: Alarm Active
    *   Bit 2: Cycle Running
    *   Bit 3: Feed Hold Active
    *   Bit 5: Spindle Running
*   **CNC Mode Word (R6201)**:
    *   Bits indicate active mode: 0:MEM/AUTO, 1:MDI, 2:ZRN/HOME, 3:MPG/HANDEL, 4:JOG, 5:INCJOG.
*   **M-Codes (R21001)**:
    *   Send value `(M_CODE_NUMBER * 1800)` to execute an M-Code.
    *   Example: `10 * 1800` executes M10 (Vacuum ON).

### IO Coils (FC01)

Read via `read_coils(0, 41)`. Note that some functions are mapped to multiple coils depending on the specific relay triggered.

*   **Coil 12:** Vacuum Pump
*   **Coils 14 or 18:** Forward Stopper
*   **Coils 15 or 19:** Left Stopper
*   **Coils 16 or 20:** Right Stopper

### System Diagnostics

These registers update at high frequency and indicate the internal state machine of the CNC:

*   **R10032 & R10033**: Modal State (ASCII). e.g., 65='A', 66='B', 68='D'.
*   **R10034**: Logic Step. Integer sequence indicating macro execution or buffer prep.
*   **R10019**: Sync Flag. When this turns to `4` then `0`, an operation has completed.

## Troubleshooting

1.  **"Poller Error: list index out of range"**: You are trying to extract a register index that exceeds the `count` requested in the block read. Expand the block read `count`.
2.  **Old Data / UI not updating**: The PWA cache is stubborn or old Python processes are hanging the port. Instruct the user to run `.\modbus_web\nuclear_restart.ps1`.
