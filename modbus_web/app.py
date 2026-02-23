"""
LNC MW2200A – Modbus TCP Web Interface
Reads machine status, axis positions, spindle/feed data and lot counters
from the LNC controller's built-in Modbus TCP server (port 502).

Register map (LNC Modbus TCP, holding registers, 0-based addresses):
  Machine status word  – R[0]   (bit flags)
  Axis X position      – R[1]   (× 0.001 mm, signed 32-bit via 2 regs)
  Axis Y position      – R[3]
  Axis Z position      – R[5]
  Spindle speed        – R[7]   (RPM)
  Feed rate            – R[8]   (mm/min)
  Active alarm code    – R[9]
  Program number       – R[10]
  Lot counter          – R[11]  (parts produced in current lot)
  Lot target           – R[12]  (target parts for current lot)
  Lot ID               – R[13]  (current lot identifier)

  Diagnostic registers (from Eth_ModbusServerTCP.ini, 0-based PDU = ini value − 1):
  Connection status    – R[5000] (OpenPortResultAddr=5001)
  Idle time            – R[5001] (IdleTimeAddr=5002)
  Packet counter       – R[5002] (CounterAddr=5003)
  Error data           – R[5003] (ErrDataAddr=5004)
  Error address        – R[5004] (ErrAddrAddr=5005)
  Packets sent         – R[5005] (PkgThisAddr=5006)
  Packets received     – R[5006] (PkgOtherAddr=5007)
  Packets responded    – R[5007] (PkgRspAddr=5008)
  Exception packets    – R[5008] (PkgExcptionAddr=5009)

Status word bit map:
  bit 0 – Emergency Stop active
  bit 1 – Alarm active
  bit 2 – Cycle running
  bit 3 – Feed hold
  bit 4 – Homing in progress
  bit 5 – Spindle running
  bit 6 – Program paused
  bit 7 – Door open

Coil map (discrete outputs, 0-based):
  coil 0 – Cycle Start
  coil 1 – Feed Hold
  coil 2 – Reset / Clear Alarm
  coil 3 – Spindle CW
  coil 4 – Spindle CCW
  coil 5 – Coolant ON
  coil 6 – E-Stop (write 1 to trigger software E-Stop)
  coil 7 – Lot Reset (write 1 to reset lot counter)
"""

import os
import struct
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

from flask import Flask, jsonify, render_template, request, abort
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

# ---------------------------------------------------------------------------
# Configuration (override with environment variables)
# ---------------------------------------------------------------------------
MODBUS_HOST = os.environ.get("MODBUS_HOST", "192.168.1.100")
MODBUS_PORT = int(os.environ.get("MODBUS_PORT", "502"))
MODBUS_UNIT = int(os.environ.get("MODBUS_UNIT", "1"))
POLL_INTERVAL = float(os.environ.get("POLL_INTERVAL", "0.5"))   # seconds
WEB_HOST = os.environ.get("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.environ.get("WEB_PORT", "5000"))
WEB_DEBUG = os.environ.get("WEB_DEBUG", "false").lower() == "true"

# Holding register start addresses (0-based)
REG_STATUS = 0
REG_X_LO = 1      # 32-bit position split across two 16-bit registers
REG_X_HI = 2
REG_Y_LO = 3
REG_Y_HI = 4
REG_Z_LO = 5
REG_Z_HI = 6
REG_SPINDLE = 7
REG_FEED = 8
REG_ALARM = 9
REG_PROGRAM = 10
REG_LOT_COUNT = 11
REG_LOT_TARGET = 12
REG_LOT_ID = 13

# Diagnostic registers from Eth_ModbusServerTCP.ini.
# The ini file uses 1-based controller notation; subtract 1 for 0-based PDU.
REG_CONN_STATUS    = 5000   # OpenPortResultAddr=5001
REG_IDLE_TIME      = 5001   # IdleTimeAddr=5002  (connection idle seconds)
REG_PKT_COUNTER    = 5002   # CounterAddr=5003   (total packets processed)
REG_ERR_DATA       = 5003   # ErrDataAddr=5004
REG_ERR_ADDR       = 5004   # ErrAddrAddr=5005
REG_PKG_THIS       = 5005   # PkgThisAddr=5006   (packets sent by server)
REG_PKG_OTHER      = 5006   # PkgOtherAddr=5007  (packets received)
REG_PKG_RSP        = 5007   # PkgRspAddr=5008    (packets responded)
REG_PKG_EXCEPTION  = 5008   # PkgExcptionAddr=5009 (exception packets)

# Number of diagnostic registers to read in one block starting at REG_CONN_STATUS
_DIAG_REG_COUNT = REG_PKG_EXCEPTION - REG_CONN_STATUS + 1  # 9 registers

# Coil addresses (0-based)
COIL_CYCLE_START = 0
COIL_FEED_HOLD = 1
COIL_RESET = 2
COIL_SPINDLE_CW = 3
COIL_SPINDLE_CCW = 4
COIL_COOLANT = 5
COIL_ESTOP = 6
COIL_LOT_RESET = 7

# Allowed coil commands exposed to the API
ALLOWED_COMMANDS = {
    "cycle_start": COIL_CYCLE_START,
    "feed_hold": COIL_FEED_HOLD,
    "reset": COIL_RESET,
    "spindle_cw": COIL_SPINDLE_CW,
    "spindle_ccw": COIL_SPINDLE_CCW,
    "coolant": COIL_COOLANT,
    "estop": COIL_ESTOP,
    "lot_reset": COIL_LOT_RESET,
}


# ---------------------------------------------------------------------------
# Machine state (updated by the polling thread)
# ---------------------------------------------------------------------------
@dataclass
class MachineState:
    connected: bool = False
    status_word: int = 0
    x_pos: float = 0.0        # mm
    y_pos: float = 0.0
    z_pos: float = 0.0
    spindle_rpm: int = 0
    feed_rate: int = 0        # mm/min
    alarm_code: int = 0
    program_number: int = 0
    lot_count: int = 0
    lot_target: int = 0
    lot_id: int = 0
    conn_status: int = 0
    idle_time_s: int = 0       # seconds the Modbus connection has been idle
    pkt_counter: int = 0       # total Modbus packets processed by controller
    pkt_exception: int = 0     # exception (error) packets
    last_update: float = 0.0
    last_error: str = ""

    # Cycle / runtime tracking (computed by the poller, not from registers)
    current_cycle_time_s: float = 0.0   # elapsed time of the current cycle
    total_cycle_time_s: float = 0.0     # accumulated machining time this session

    # Decoded status flags
    estop_active: bool = False
    alarm_active: bool = False
    cycle_running: bool = False
    feed_hold_active: bool = False
    homing: bool = False
    spindle_running: bool = False
    program_paused: bool = False
    door_open: bool = False

    def decode_status_word(self) -> None:
        sw = self.status_word
        self.estop_active = bool(sw & (1 << 0))
        self.alarm_active = bool(sw & (1 << 1))
        self.cycle_running = bool(sw & (1 << 2))
        self.feed_hold_active = bool(sw & (1 << 3))
        self.homing = bool(sw & (1 << 4))
        self.spindle_running = bool(sw & (1 << 5))
        self.program_paused = bool(sw & (1 << 6))
        self.door_open = bool(sw & (1 << 7))


_state = MachineState()
_state_lock = threading.Lock()


def _regs_to_int32(lo: int, hi: int) -> int:
    """Combine two 16-bit Modbus registers into a signed 32-bit integer."""
    raw = (hi << 16) | (lo & 0xFFFF)
    return struct.unpack(">i", struct.pack(">I", raw))[0]


# ---------------------------------------------------------------------------
# Polling thread
# ---------------------------------------------------------------------------
class ModbusPoller(threading.Thread):
    """Background thread that continuously polls the LNC controller."""

    def __init__(self) -> None:
        super().__init__(daemon=True, name="ModbusPoller")
        self._client: Optional[ModbusTcpClient] = None
        self._cycle_was_running: bool = False
        self._cycle_start: Optional[float] = None
        self._total_cycle_s: float = 0.0

    def _connect(self) -> bool:
        try:
            if self._client:
                self._client.close()
            self._client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
            return self._client.connect()
        except Exception as exc:  # noqa: BLE001
            with _state_lock:
                _state.connected = False
                _state.last_error = str(exc)
            return False

    def _poll(self) -> None:
        assert self._client is not None
        try:
            # Read the main register block (14 registers: 0–13)
            rr = self._client.read_holding_registers(
                address=REG_STATUS, count=14, device_id=MODBUS_UNIT
            )
            if rr.isError():
                raise ModbusException(f"Register read error: {rr}")

            regs = rr.registers

            # Read diagnostic register block (5000–5008, 9 registers)
            rr_diag = self._client.read_holding_registers(
                address=REG_CONN_STATUS, count=_DIAG_REG_COUNT, device_id=MODBUS_UNIT
            )
            if rr_diag.isError():
                diag = [0] * _DIAG_REG_COUNT
            else:
                diag = rr_diag.registers

            # Cycle-time tracking (computed from the cycle_running status bit)
            now = time.time()
            cycle_running_now = bool(regs[REG_STATUS] & (1 << 2))
            if cycle_running_now and not self._cycle_was_running:
                self._cycle_start = now
            elif not cycle_running_now and self._cycle_was_running:
                if self._cycle_start is not None:
                    self._total_cycle_s += now - self._cycle_start
                    self._cycle_start = None
            self._cycle_was_running = cycle_running_now

            current_cycle_s = (now - self._cycle_start) if self._cycle_start is not None else 0.0

            with _state_lock:
                _state.connected = True
                _state.last_error = ""
                _state.status_word = regs[REG_STATUS]
                _state.x_pos = _regs_to_int32(regs[REG_X_LO], regs[REG_X_HI]) / 1000.0
                _state.y_pos = _regs_to_int32(regs[REG_Y_LO], regs[REG_Y_HI]) / 1000.0
                _state.z_pos = _regs_to_int32(regs[REG_Z_LO], regs[REG_Z_HI]) / 1000.0
                _state.spindle_rpm = regs[REG_SPINDLE]
                _state.feed_rate = regs[REG_FEED]
                _state.alarm_code = regs[REG_ALARM]
                _state.program_number = regs[REG_PROGRAM]
                _state.lot_count = regs[REG_LOT_COUNT]
                _state.lot_target = regs[REG_LOT_TARGET]
                _state.lot_id = regs[REG_LOT_ID]
                _state.conn_status   = diag[REG_CONN_STATUS   - REG_CONN_STATUS]
                _state.idle_time_s   = diag[REG_IDLE_TIME      - REG_CONN_STATUS]
                _state.pkt_counter   = diag[REG_PKT_COUNTER    - REG_CONN_STATUS]
                _state.pkt_exception = diag[REG_PKG_EXCEPTION  - REG_CONN_STATUS]
                _state.current_cycle_time_s = current_cycle_s
                _state.total_cycle_time_s   = self._total_cycle_s + current_cycle_s
                _state.last_update = now
                _state.decode_status_word()

        except Exception as exc:  # noqa: BLE001
            with _state_lock:
                _state.connected = False
                _state.last_error = str(exc)
            self._connect()

    def run(self) -> None:
        while True:
            if self._client is None or not self._client.is_socket_open():
                self._connect()
            if self._client and self._client.is_socket_open():
                self._poll()
            time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
app = Flask(__name__)


def _state_snapshot() -> dict:
    with _state_lock:
        snap = asdict(_state)
    snap["lot_progress_pct"] = (
        round(snap["lot_count"] / snap["lot_target"] * 100, 1)
        if snap["lot_target"] > 0
        else 0
    )
    return snap


@app.route("/")
def index():
    return render_template("index.html",
                           modbus_host=MODBUS_HOST,
                           modbus_port=MODBUS_PORT)


@app.route("/api/status")
def api_status():
    """Return current machine state as JSON."""
    return jsonify(_state_snapshot())


@app.route("/api/command", methods=["POST"])
def api_command():
    """
    Write a single coil to issue a command.
    Body: { "command": "<name>", "value": true|false }
    """
    body = request.get_json(force=True, silent=True) or {}
    command = body.get("command", "")
    value = bool(body.get("value", True))

    if command not in ALLOWED_COMMANDS:
        abort(400, description=f"Unknown command '{command}'. "
              f"Allowed: {list(ALLOWED_COMMANDS)}")

    coil_addr = ALLOWED_COMMANDS[command]
    client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    try:
        if not client.connect():
            abort(503, description="Cannot connect to Modbus server")
        result = client.write_coil(coil_addr, value, device_id=MODBUS_UNIT)
        if result.isError():
            abort(502, description=f"Modbus write error: {result}")
    except ModbusException as exc:
        abort(502, description=str(exc))
    finally:
        client.close()

    return jsonify({"ok": True, "command": command, "value": value})


@app.route("/api/diagnostics")
def api_diagnostics():
    """
    Return connection configuration, the full register/coil map, and the
    last Modbus error so operators can quickly identify endpoint problems.
    """
    with _state_lock:
        connected = _state.connected
        last_error = _state.last_error
        conn_status = _state.conn_status
        last_update = _state.last_update

    register_map = {
        "holding_registers": [
            {"address": REG_STATUS,     "description": "Machine status word (bit flags)"},
            {"address": REG_X_LO,       "description": "X position – low word (×0.001 mm, signed 32-bit with next reg)"},
            {"address": REG_X_HI,       "description": "X position – high word"},
            {"address": REG_Y_LO,       "description": "Y position – low word"},
            {"address": REG_Y_HI,       "description": "Y position – high word"},
            {"address": REG_Z_LO,       "description": "Z position – low word"},
            {"address": REG_Z_HI,       "description": "Z position – high word"},
            {"address": REG_SPINDLE,    "description": "Spindle speed (RPM)"},
            {"address": REG_FEED,       "description": "Feed rate (mm/min)"},
            {"address": REG_ALARM,      "description": "Active alarm code"},
            {"address": REG_PROGRAM,    "description": "Program number"},
            {"address": REG_LOT_COUNT,  "description": "Lot count (parts produced)"},
            {"address": REG_LOT_TARGET, "description": "Lot target"},
            {"address": REG_LOT_ID,     "description": "Lot ID"},
            {"address": REG_CONN_STATUS,   "description": "Connection status (OpenPortResultAddr=5001 in ini)"},
            {"address": REG_IDLE_TIME,     "description": "Connection idle time – seconds (IdleTimeAddr=5002)"},
            {"address": REG_PKT_COUNTER,   "description": "Total Modbus packets processed (CounterAddr=5003)"},
            {"address": REG_ERR_DATA,      "description": "Last error data value (ErrDataAddr=5004)"},
            {"address": REG_ERR_ADDR,      "description": "Last error register address (ErrAddrAddr=5005)"},
            {"address": REG_PKG_THIS,      "description": "Packets sent by server (PkgThisAddr=5006)"},
            {"address": REG_PKG_OTHER,     "description": "Packets received from client (PkgOtherAddr=5007)"},
            {"address": REG_PKG_RSP,       "description": "Packets responded (PkgRspAddr=5008)"},
            {"address": REG_PKG_EXCEPTION, "description": "Exception (error) packets (PkgExcptionAddr=5009)"},
        ],
        "coils": [
            {"address": COIL_CYCLE_START, "name": "cycle_start",  "description": "Cycle Start"},
            {"address": COIL_FEED_HOLD,   "name": "feed_hold",    "description": "Feed Hold"},
            {"address": COIL_RESET,       "name": "reset",        "description": "Reset / Clear Alarm"},
            {"address": COIL_SPINDLE_CW,  "name": "spindle_cw",   "description": "Spindle CW"},
            {"address": COIL_SPINDLE_CCW, "name": "spindle_ccw",  "description": "Spindle CCW"},
            {"address": COIL_COOLANT,     "name": "coolant",      "description": "Coolant ON"},
            {"address": COIL_ESTOP,       "name": "estop",        "description": "Software E-Stop"},
            {"address": COIL_LOT_RESET,   "name": "lot_reset",    "description": "Lot Reset"},
        ],
        "status_bits": [
            {"bit": 0, "description": "Emergency Stop active"},
            {"bit": 1, "description": "Alarm active"},
            {"bit": 2, "description": "Cycle running"},
            {"bit": 3, "description": "Feed Hold active"},
            {"bit": 4, "description": "Homing in progress"},
            {"bit": 5, "description": "Spindle running"},
            {"bit": 6, "description": "Program paused"},
            {"bit": 7, "description": "Door open"},
        ],
    }

    return jsonify({
        "config": {
            "modbus_host": MODBUS_HOST,
            "modbus_port": MODBUS_PORT,
            "modbus_unit_id": MODBUS_UNIT,
            "poll_interval_s": POLL_INTERVAL,
            "authentication": "none – Modbus TCP has no built-in authentication",
        },
        "connection": {
            "connected": connected,
            "last_error": last_error or None,
            "conn_status_register": conn_status,
            "last_update": last_update or None,
        },
        "register_map": register_map,
        "hints": [
            "Ensure the LNC controller has Modbus TCP enabled: parameter 45010 = 1",
            "Default port is 502 (configurable in Eth_ModbusServerTCP.ini on the controller)",
            "Unit ID is typically 1; change MODBUS_UNIT env-var if your controller uses a different slave ID",
            "Register addresses are 0-based (Modbus PDU). Some tools display 1-based addresses (add 1).",
            "Use /api/scan to read raw register values and verify the endpoint mapping",
            "Cycle time and total session machining time are computed by the web app from the cycle_running status bit – they reset when the web server restarts",
            "idle_time_s (R[5001]) is the Modbus connection idle counter from the controller, not total machine uptime",
        ],
    })


@app.route("/api/scan")
def api_scan():
    """
    Open a fresh Modbus connection and read key register ranges, returning
    raw values. Useful for diagnosing which endpoints actually respond and
    verifying register assignments without relying on the polling thread.
    """
    results: dict = {
        "config": {
            "modbus_host": MODBUS_HOST,
            "modbus_port": MODBUS_PORT,
            "modbus_unit_id": MODBUS_UNIT,
        },
        "scans": [],
        "errors": [],
    }

    client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    try:
        if not client.connect():
            results["errors"].append(
                f"Cannot connect to {MODBUS_HOST}:{MODBUS_PORT} – "
                "check host/port and that parameter 45010=1 on the controller"
            )
            return jsonify(results)

        # --- Holding registers 0–13 (main data block) ---
        _main_desc = {
            0: "Machine status word",
            1: "X pos – low word (×0.001 mm)",
            2: "X pos – high word",
            3: "Y pos – low word",
            4: "Y pos – high word",
            5: "Z pos – low word",
            6: "Z pos – high word",
            7: "Spindle speed (RPM)",
            8: "Feed rate (mm/min)",
            9: "Active alarm code",
            10: "Program number",
            11: "Lot count",
            12: "Lot target",
            13: "Lot ID",
        }
        try:
            rr = client.read_holding_registers(address=0, count=14, device_id=MODBUS_UNIT)
            if rr.isError():
                results["errors"].append(f"Holding regs 0-13 error: {rr}")
            else:
                for i, val in enumerate(rr.registers):
                    results["scans"].append({
                        "type": "holding_register",
                        "address": i,
                        "description": _main_desc.get(i, ""),
                        "raw_value": val,
                        "hex": hex(val),
                    })
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(f"Holding regs 0-13 exception: {exc}")

        # --- Diagnostic registers 5000–5008 (connection/packet stats) ---
        try:
            rr = client.read_holding_registers(address=REG_CONN_STATUS, count=_DIAG_REG_COUNT, device_id=MODBUS_UNIT)
            if rr.isError():
                results["errors"].append(f"Diagnostic regs {REG_CONN_STATUS}-{REG_PKG_EXCEPTION} error: {rr}")
            else:
                _diag_desc = {
                    REG_CONN_STATUS:   "Connection status",
                    REG_IDLE_TIME:     "Idle time (s)",
                    REG_PKT_COUNTER:   "Packet counter",
                    REG_ERR_DATA:      "Error data",
                    REG_ERR_ADDR:      "Error address",
                    REG_PKG_THIS:      "Packets sent",
                    REG_PKG_OTHER:     "Packets received",
                    REG_PKG_RSP:       "Packets responded",
                    REG_PKG_EXCEPTION: "Exception packets",
                }
                for offset, val in enumerate(rr.registers):
                    addr = REG_CONN_STATUS + offset
                    results["scans"].append({
                        "type": "holding_register",
                        "address": addr,
                        "description": _diag_desc.get(addr, ""),
                        "raw_value": val,
                        "hex": hex(val),
                    })
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(f"Diagnostic regs exception: {exc}")

        # --- Coils 0–7 ---
        _coil_desc = {
            0: "Cycle Start",
            1: "Feed Hold",
            2: "Reset / Clear Alarm",
            3: "Spindle CW",
            4: "Spindle CCW",
            5: "Coolant ON",
            6: "Software E-Stop",
            7: "Lot Reset",
        }
        try:
            rc = client.read_coils(address=0, count=8, device_id=MODBUS_UNIT)
            if rc.isError():
                results["errors"].append(f"Coils 0-7 error: {rc}")
            else:
                for i, val in enumerate(rc.bits[:8]):
                    results["scans"].append({
                        "type": "coil",
                        "address": i,
                        "description": _coil_desc.get(i, ""),
                        "raw_value": int(val),
                        "hex": "",
                    })
        except Exception as exc:  # noqa: BLE001
            results["errors"].append(f"Coils 0-7 exception: {exc}")

    except Exception as exc:  # noqa: BLE001
        results["errors"].append(f"Unexpected error during scan: {exc}")
    finally:
        client.close()

    return jsonify(results)


@app.route("/api/lot/set_target", methods=["POST"])
def api_set_lot_target():
    """
    Write a new lot target value to REG_LOT_TARGET.
    Body: { "target": <int> }
    """
    body = request.get_json(force=True, silent=True) or {}
    target = body.get("target")
    if not isinstance(target, (int, float)) or isinstance(target, bool) or target < 0 or target != int(target):
        abort(400, description="'target' must be a non-negative integer")
    target = int(target)

    client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    try:
        if not client.connect():
            abort(503, description="Cannot connect to Modbus server")
        result = client.write_register(
            REG_LOT_TARGET, target & 0xFFFF, device_id=MODBUS_UNIT
        )
        if result.isError():
            abort(502, description=f"Modbus write error: {result}")
    except ModbusException as exc:
        abort(502, description=str(exc))
    finally:
        client.close()

    return jsonify({"ok": True, "lot_target": target})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    poller = ModbusPoller()
    poller.start()
    app.run(host=WEB_HOST, port=WEB_PORT, debug=WEB_DEBUG, use_reloader=False)
