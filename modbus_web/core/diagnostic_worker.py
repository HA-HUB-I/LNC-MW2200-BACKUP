import threading
import time
import csv
import os
from datetime import datetime
from pymodbus.client import ModbusTcpClient
from .config import MODBUS_HOST, MODBUS_PORT, MODBUS_UNIT

class DiagnosticWorker(threading.Thread):
    def __init__(self, watch_addresses: list):
        super().__init__(daemon=True, name="DiagnosticWorker")
        self.watch_addresses = watch_addresses
        self.client = ModbusTcpClient(host=MODBUS_HOST, port=MODBUS_PORT)
        self.log_file = "modbus_web/logs/diagnostic_history.csv"
        self.last_values = {}
        self.is_running = True
        
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Address", "RawValue", "HumanValue", "Delta"])

    def _log_change(self, addr, val, prev_val):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        delta = val - prev_val
        
        if addr in [10032, 10033] and 32 <= val <= 126:
            human_val = f"'{chr(val)}'"
        elif addr == 21001:
            human_val = f"M{val // 1800 if val > 0 else 0}"
        else:
            human_val = str(val)
        
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, addr, val, human_val, delta])

    def run(self):
        while self.is_running:
            if not self.client.is_socket_open():
                # Ако машината е изключена, не натоварваме системата с бързи опити
                if not self.client.connect():
                    time.sleep(10.0) # Чакаме 10 секунди за диагностиката
                    continue
            
            try:
                for addr in self.watch_addresses:
                    rr = self.client.read_holding_registers(address=addr, count=1, device_id=MODBUS_UNIT)
                    if not rr.isError():
                        val = rr.registers[0]
                        if addr in self.last_values and val != self.last_values[addr]:
                            self._log_change(addr, val, self.last_values[addr])
                        self.last_values[addr] = val
                
                time.sleep(0.1) # Бърз режим само при активна връзка
            except Exception:
                self.client.close()
                time.sleep(5.0)

    def stop(self):
        self.is_running = False
        self.client.close()
