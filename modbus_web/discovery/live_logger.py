import socket
import struct
import time
import datetime
import os

HOST = "192.168.0.113"
PORT = 502
UNIT = 0 # Използваме Unit 0
LOG_FILE = "modbus_web/discovery/discovery_history.log"

# Речник с познатите ни регистри
REGISTER_MAP = {
    0:     "Machine Status Word",
    1007:  "Spindle RPM",
    11565: "Candidate X",
    11570: "System Timer (ms)",
    11633: "Candidate Z1",
    11638: "Live Velocity (mm/min)",
    12033: "Candidate Z2 (Work Z?)",
    12038: "Work Y",
    12065: "Work X",
    12070: "Candidate Abs Y",
    10006: "G-Code Modal Group (G64/G66)",
    10032: "Modal State A (ASCII)",
    10034: "Modal State B (Logic Step)",
    6201:  "CNC Mode Word (JOG/AUTO)",
    8102:  "G-Code Line Number"
}

def decode_human(addr, val):
    """Превежда суровата стойност в човешки вид."""
    name = REGISTER_MAP.get(addr, f"R{addr}")
    
    # Координати (0.001 mm)
    if addr in [11565, 11633, 12033, 12038, 12065, 12070, 11575]:
        s_val = struct.unpack(">h", struct.pack(">H", val & 0xFFFF))[0]
        return f"{name}: {s_val/1000.0:.3f} mm"
    
    # Скорости
    if addr == 1007: return f"{name}: {val} RPM"
    if addr == 11638: return f"{name}: {val} mm/min"
    
    # Модални състояния (ASCII)
    if addr == 10032 and val > 0:
        char = chr(val) if 32 <= val <= 126 else "?"
        return f"{name}: {val} ('{char}')"
        
    # Битови флагове (Status Word R0)
    if addr == 0:
        bits = []
        if val & (1 << 0): bits.append("E-STOP")
        if val & (1 << 1): bits.append("ALARM")
        if val & (1 << 2): bits.append("CYCLE RUN")
        if val & (1 << 5): bits.append("SPINDLE RUN")
        return f"{name}: {val} ({'|'.join(bits) if bits else 'IDLE'})"

    return f"{name}: {val}"

def raw_read(sock, start, count):
    tid = 1
    pdu = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
    try:
        sock.sendall(mbap + pdu)
        resp = b""
        while len(resp) < 9:
            chunk = sock.recv(1)
            if not chunk: return None
            resp += chunk
        bc = resp[8]
        data = b""
        while len(data) < bc:
            chunk = sock.recv(bc - len(data))
            if not chunk: break
            data += chunk
        return [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(bc // 2)]
    except: return None

def log_msg(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}\n"
    print(entry, end="")
    with open(LOG_FILE, "a", encoding="utf-8") as f: f.write(entry)

def main():
    print(f"Human-Friendly Logger started on {HOST} (Unit {UNIT})...")
    last_vals = {}
    
    # Диапазони за следене
    MONITOR = [(0, 20), (1000, 20), (6200, 10), (8100, 10), (10000, 50), (11500, 150), (12000, 100)]
    
    try:
        while True:
            s = socket.create_connection((HOST, PORT), timeout=2)
            current = {}
            for start, count in MONITOR:
                regs = raw_read(s, start, count)
                if regs:
                    for i, v in enumerate(regs): current[start+i] = v
            s.close()

            if last_vals:
                for addr, val in current.items():
                    if addr in last_vals and val != last_vals[addr]:
                        # Логваме само ако промяната не е в бързия таймер (освен ако не е голяма)
                        if addr == 11570 and abs(val - last_vals[addr]) < 500: continue
                        
                        msg = decode_human(addr, val)
                        prev_msg = decode_human(addr, last_vals[addr])
                        log_msg(f"{msg} (was {last_vals[addr]})")
            
            last_vals = current
            time.sleep(0.3)
    except KeyboardInterrupt: print("Stopped.")
    except Exception as e: print(f"Error: {e}")

if __name__ == "__main__":
    main()
