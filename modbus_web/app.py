"""
LNC MW2200A – Modbus TCP Web Interface
REVERTED TO WORKING STATE - UNIT 1 - Turn 28/30 Baseline
"""

import os
import pathlib
import struct
import threading
import time
from dataclasses import dataclass, field, asdict
from flask import Flask, jsonify, render_template, request, send_from_directory
from pymodbus.client import ModbusTcpClient

# --- Configuration ---
MODBUS_HOST = "192.168.0.113"
MODBUS_PORT = 502
MODBUS_UNIT = 1 
POLL_INTERVAL = 0.5
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000

@dataclass
class MachineState:
    connected: bool = False
    status_word: int = 0
    x_pos: float = 0.0
    y_pos: float = 0.0
    z_pos: float = 0.0
    abs_x_pos: float = 0.0
    abs_y_pos: float = 0.0
    abs_z_pos: float = 0.0
    spindle_rpm: int = 0
    feed_rate: int = 0
    program_number: int = 0
    lot_count: int = 0
    lot_target: int = 0
    current_cycle_time_s: float = 0.0
    total_cycle_time_s: float = 0.0
    estop_active: bool = False
    alarm_active: bool = False
    cycle_running: bool = False
    feed_hold_active: bool = False
    spindle_running: bool = False
    door_open: bool = False
    vacuum_on: bool = False
    forward_pos_on: bool = False
    left_pos_on: bool = False
    right_pos_on: bool = False
    spindle_on: bool = False
    cnc_mode: str = "IDLE"
    cnc_mode_word: int = 0
    gcode_line: int = 0
    last_update: float = 0.0
    feed_override_pct: int = 100
    spindle_override_pct: int = 100

    def decode_status_word(self) -> None:
        sw = self.status_word
        self.estop_active = bool(sw & (1 << 0))
        self.alarm_active = bool(sw & (1 << 1))
        self.cycle_running = bool(sw & (1 << 2))
        self.feed_hold_active = bool(sw & (1 << 3))
        self.spindle_running = bool(sw & (1 << 5))
        self.door_open = bool(sw & (1 << 7))

    def decode_cnc_mode(self) -> None:
        mw = self.cnc_mode_word
        _modes = {0:"MEM", 1:"MDI", 2:"ZRN", 3:"MPG", 4:"JOG", 5:"INCJOG", 6:"RAPID"}
        for bit, name in _modes.items():
            if mw & (1 << bit):
                self.cnc_mode = name
                return
        self.cnc_mode = "IDLE"

def _regs_to_int16(val: int) -> int:
    return struct.unpack(">h", struct.pack(">H", val & 0xFFFF))[0]

_state = MachineState()
_state_lock = threading.Lock()

class ModbusPoller(threading.Thread):
    def __init__(self) -> None:
        super().__init__(daemon=True, name="ModbusPoller")
        self._client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
        self._cycle_start = None
        self._total_cycle_s = 0.0
        self._cycle_was_running = False

    def _poll(self) -> None:
        try:
            # 1. Основен блок (0-13)
            rr_main = self._client.read_holding_registers(address=0, count=14, device_id=MODBUS_UNIT)
            main = rr_main.registers if not rr_main.isError() else [0]*14

            # 2. Обороти (1000-1010)
            rr_speed = self._client.read_holding_registers(address=1000, count=11, device_id=MODBUS_UNIT)
            speed = rr_speed.registers if not rr_speed.isError() else [0]*11

            # 3. Координати (11565-11645)
            rr_coord = self._client.read_holding_registers(address=11565, count=80, device_id=MODBUS_UNIT)
            coord = rr_coord.registers if not rr_coord.isError() else [0]*80

            # 4. Режими (6100-6202)
            rr_mode = self._client.read_holding_registers(address=6100, count=102, device_id=MODBUS_UNIT)
            mode_regs = rr_mode.registers if not rr_mode.isError() else [0]*102

            # 5. Overrides (8060-8110)
            rr_sys = self._client.read_holding_registers(address=8060, count=50, device_id=MODBUS_UNIT)
            sys_regs = rr_sys.registers if not rr_sys.isError() else [0]*50

            # 6. Coil статуси
            rr_coils = self._client.read_coils(address=0, count=41, device_id=MODBUS_UNIT)
            coils = rr_coils.bits if not rr_coils.isError() else [False]*41

            now = time.time()
            running = bool(main[0] & (1 << 2))
            if running and not self._cycle_was_running: self._cycle_start = now
            elif not running and self._cycle_was_running and self._cycle_start:
                self._total_cycle_s += (now - self._cycle_start)
                self._cycle_start = None
            self._cycle_was_running = running
            cur_c = (now - self._cycle_start) if self._cycle_start else 0.0

            with _state_lock:
                _state.connected = True
                _state.status_word = main[0]
                
                # --- ВРЪЩАНЕ НА ЖИВИТЕ КООРДИНАТИ (С РАЗМЯНА) ---
                _state.x_pos = _regs_to_int16(coord[5]) / 1000.0   # R11570 (Беше 12.149)
                _state.y_pos = _regs_to_int16(coord[0]) / 1000.0   # R11565 (Беше 10.187)
                _state.z_pos = _regs_to_int16(coord[68]) / 1000.0  # R11633

                _state.spindle_rpm = speed[7] # R1007
                _state.feed_rate = coord[73] # R11638
                
                _state.cnc_mode_word = mode_regs[101] # R6201
                _state.decode_cnc_mode()
                _state.decode_status_word()
                
                _state.vacuum_on = coils[12]
                _state.forward_pos_on = coils[14]
                _state.left_pos_on = coils[15]
                _state.right_pos_on = coils[16]
                _state.spindle_on = coils[7] or coils[8] or coils[3]
                
                _state.feed_override_pct = sys_regs[7] // 10 if len(sys_regs) > 7 else 100
                _state.spindle_override_pct = sys_regs[9] // 10 if len(sys_regs) > 9 else 100
                _state.gcode_line = sys_regs[42]
                _state.program_number = main[10]
                _state.lot_count = main[11]
                _state.lot_target = main[12]
                
                _state.current_cycle_time_s = cur_c
                _state.total_cycle_time_s = self._total_cycle_s + cur_c
                _state.last_update = now

        except Exception:
            with _state_lock: _state.connected = False
            self._client.connect()

    def run(self) -> None:
        while True:
            if not self._client.is_socket_open(): self._client.connect()
            if self._client.is_socket_open(): self._poll()
            time.sleep(POLL_INTERVAL)

app = Flask(__name__)
@app.route("/")
def index(): return render_template("index.html")
@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')
@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')
@app.route("/api/status")
def api_status():
    with _state_lock: return jsonify(asdict(_state))
@app.route("/api/command", methods=["POST"])
def api_command():
    body = request.get_json(force=True, silent=True) or {}
    cmd = body.get("command")
    client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
    if client.connect():
        if cmd == "cycle_start": client.write_coil(0, True, device_id=MODBUS_UNIT)
        if cmd == "feed_hold": client.write_coil(1, True, device_id=MODBUS_UNIT)
        if cmd == "reset": client.write_coil(2, True, device_id=MODBUS_UNIT)
        if cmd == "estop": client.write_coil(6, True, device_id=MODBUS_UNIT)
        client.close()
    return jsonify(ok=True)

if __name__ == "__main__":
    poller = ModbusPoller()
    poller.start()
    app.run(host="0.0.0.0", port=5000, debug=False)
