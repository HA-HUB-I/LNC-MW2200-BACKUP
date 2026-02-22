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

  Connection status    – R[5000] (OpenPortResultAddr 5001 − 1, 0-based PDU)
  Idle time            – R[5002]
  Packet counter       – R[5003]

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

# Connection status register.
# Eth_ModbusServerTCP.ini sets OpenPortResultAddr=5001 (1-based controller
# notation). Modbus PDU addressing is 0-based, so subtract 1: 5001 - 1 = 5000.
REG_CONN_STATUS = 5000

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
    last_update: float = 0.0
    last_error: str = ""

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

            # Read connection status register (5000, count 1)
            rr_conn = self._client.read_holding_registers(
                address=REG_CONN_STATUS, count=1, device_id=MODBUS_UNIT
            )
            conn_val = rr_conn.registers[0] if not rr_conn.isError() else 0

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
                _state.conn_status = conn_val
                _state.last_update = time.time()
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
