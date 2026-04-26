import threading
import time
import struct
from pymodbus.client import ModbusTcpClient
from .models import MachineState
from .config import *

def _regs_to_int16(val: int) -> int:
    return struct.unpack(">h", struct.pack(">H", val & 0xFFFF))[0]

class ModbusWorker(threading.Thread):
    def __init__(self, state: MachineState, lock: threading.Lock):
        super().__init__(daemon=True, name="ModbusWorker")
        self.state = state
        self.lock = lock
        self.client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
        
        self._cycle_start = None
        self._total_cycle_s = 0.0
        self._cycle_was_running = False

    def _poll(self):
        try:
            # 1. Main Block
            r = self.client.read_holding_registers(address=R_STATUS, count=14, device_id=MODBUS_UNIT)
            main = r.registers if not r.isError() else [0]*14

            # 2. Speeds
            r = self.client.read_holding_registers(address=R_SPEEDS, count=11, device_id=MODBUS_UNIT)
            speed = r.registers if not r.isError() else [0]*11

            # 3. Coords (11565 zone)
            r = self.client.read_holding_registers(address=R_COORDS, count=80, device_id=MODBUS_UNIT)
            coord = r.registers if not r.isError() else [0]*80

            # 4. Modes & Overrides
            r_m = self.client.read_holding_registers(address=R_MODES, count=102, device_id=MODBUS_UNIT)
            r_s = self.client.read_holding_registers(address=R_OVERRIDES, count=50, device_id=MODBUS_UNIT)
            mode_regs = r_m.registers if not r_m.isError() else [0]*102
            sys_regs = r_s.registers if not r_s.isError() else [0]*50

            # 5. Coils
            r_c = self.client.read_coils(address=0, count=41, device_id=MODBUS_UNIT)
            coils = r_c.bits if not r_c.isError() else [False]*41

            now = time.time()
            running = bool(main[0] & (1 << 2))
            if running and not self._cycle_was_running: self._cycle_start = now
            elif not running and self._cycle_was_running and self._cycle_start:
                self._total_cycle_s += (now - self._cycle_start)
                self._cycle_start = None
            self._cycle_was_running = running
            cur_c = (now - self._cycle_start) if self._cycle_start else 0.0

            with self.lock:
                s = self.state
                s.connected = True
                s.status_word = main[0]
                
                # Потвърдени координати (с размяна X/Y)
                s.x_pos = _regs_to_int16(coord[5]) / 1000.0   # R11570
                s.y_pos = _regs_to_int16(coord[0]) / 1000.0   # R11565
                s.z_pos = _regs_to_int16(coord[68]) / 1000.0  # R11633

                s.spindle_rpm = speed[7]
                s.feed_rate = coord[73]
                
                s.cnc_mode_word = mode_regs[101]
                s.decode_cnc_mode()
                s.decode_status_word()
                
                s.vacuum_on = coils[12]
                s.forward_pos_on = coils[14]
                s.left_pos_on = coils[15]
                s.right_pos_on = coils[16]
                s.spindle_on = coils[7] or coils[8] or coils[3]
                
                s.feed_override_pct = sys_regs[7] // 10 if len(sys_regs) > 7 else 100
                s.spindle_override_pct = sys_regs[9] // 10 if len(sys_regs) > 9 else 100
                s.gcode_line = sys_regs[42]
                s.program_number = main[10]
                s.lot_count = main[11]
                s.lot_target = main[12]
                
                s.current_cycle_time_s = cur_c
                s.total_cycle_time_s = self._total_cycle_s + cur_c
                s.last_update = now

        except Exception as e:
            with self.lock: self.state.connected = False
            print(f"Poller Error: {e}")

    def run(self):
        while True:
            if not self.client.is_socket_open(): self.client.connect()
            if self.client.is_socket_open(): self._poll()
            time.sleep(POLL_INTERVAL)

    def send_coil(self, addr, value=True):
        if self.client.is_socket_open():
            self.client.write_coil(addr, value, device_id=MODBUS_UNIT)
