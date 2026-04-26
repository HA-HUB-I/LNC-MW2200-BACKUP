# LNC MW2200A Modbus Web Dashboard (PWA)

This project provides real-time monitoring and control of an LNC MW2200A CNC machine via Modbus TCP.

## 🚀 Current Architecture (Clean Modules)
The backend is split into logical modules to prevent crashes and ensure easy maintainability:
- **`app.py`**: The main Flask server and API router.
- **`core/models.py`**: The `MachineState` dataclass defining all tracked variables.
- **`core/config.py`**: A unified map of all confirmed Modbus registers and addresses.
- **`core/modbus_worker.py`**: A background thread polling the machine using optimized block reads.
- **`core/diagnostic_worker.py`**: A secondary thread logging specific register changes to a CSV file (`logs/diagnostic_history.csv`).
- **`core/utils.py`**: Helper functions for handling `.nc` file uploads.

## 📱 Frontend (PWA)
The UI is a responsive Progressive Web App (PWA):
- **`templates/index.html`**: The UI skeleton.
- **`static/css/style.css`**: Styles for cards, gauges, and warning banners.
- **`static/js/app.js`**: UI update logic, unit toggling (mm/cm), and connection status handling.
- **`static/manifest.json` & `static/sw.js`**: PWA registration files.

## 📊 Verified Modbus Map
See `MODBUS_DISCOVERY.md` for the strictly verified list of registers. 
**Key findings:**
- `Unit ID` must be `1` for stable diagnostic reads.
- The machine uses `RegisterMode=-32`.
- `Work (Absolute)` coordinates are in the `12000` range (`R12032`, `R12038`, `R12034`).
- `Machine (Relative)` coordinates are in the `11500` range (`R11570`, `R11565`, `R11560`).

## 🔄 How to Restart Cleanly
If UI changes are not reflecting or python processes are hanging, run the included nuclear restart script:
```powershell
.\modbus_web\nuclear_restart.ps1
```
This kills all Python processes, clears the `__pycache__`, and starts `app.py` fresh.
