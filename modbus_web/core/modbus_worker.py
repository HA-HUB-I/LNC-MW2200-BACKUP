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
            # 1. Основен блок (0-13)
            r_main = self.client.read_holding_registers(address=0, count=14, device_id=MODBUS_UNIT)
            main = r_main.registers if not r_main.isError() else [0]*14

            # 2. Обороти (1000-1010)
            r_speed = self.client.read_holding_registers(address=1000, count=11, device_id=MODBUS_UNIT)
            speed = r_speed.registers if not r_speed.isError() else [0]*11

            # 3. Координатен блок (11560-11650)
            r_coord = self.client.read_holding_registers(address=R_COORDS_BLOCK, count=R_COORD_COUNT, device_id=MODBUS_UNIT)
            coord = r_coord.registers if not r_coord.isError() else [0]*R_COORD_COUNT

            # 4. Абсолютен блок (12000-12050)
            r_abs = self.client.read_holding_registers(address=R_ABS_BLOCK, count=R_ABS_COUNT, device_id=MODBUS_UNIT)
            abs_regs = r_abs.registers if not r_abs.isError() else [0]*R_ABS_COUNT

            # 5. Режими (6100-6202)
            r_mode = self.client.read_holding_registers(address=6100, count=102, device_id=MODBUS_UNIT)
            mode_regs = r_mode.registers if not r_mode.isError() else [0]*102
            
            # 6. Overrides (8060-8110)
            r_sys = self.client.read_holding_registers(address=8060, count=50, device_id=MODBUS_UNIT)
            sys_regs = r_sys.registers if not r_sys.isError() else [0]*50

            # 7. Coils
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
                
                # --- МАШИННИ КООРДИНАТИ (Machine / Relative) ---
                s.x_pos = _regs_to_int16(coord[10]) / 1000.0   # R11570
                s.y_pos = _regs_to_int16(coord[5]) / 1000.0    # R11565
                s.z_pos = _regs_to_int16(coord[0]) / 1000.0    # R11560

                # --- АБСОЛЮТНИ КООРДИНАТИ (Absolute / Work G54) ---
                s.abs_x_pos = _regs_to_int16(abs_regs[32]) / 1000.0 # R12032 ✅
                s.abs_y_pos = _regs_to_int16(abs_regs[38]) / 1000.0 # R12038 ✅
                s.abs_z_pos = _regs_to_int16(abs_regs[34]) / 1000.0 # R12034 ✅

                s.spindle_rpm = speed[7]
                s.feed_rate = coord[78] # R11638

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

    def write_coil(self, addr, value=True):
        if self.client.is_socket_open():
            return self.client.write_coil(address=addr, value=value, device_id=MODBUS_UNIT)

    def write_register(self, addr, value):
        if self.client.is_socket_open():
            return self.client.write_register(address=addr, value=value, device_id=MODBUS_UNIT)
