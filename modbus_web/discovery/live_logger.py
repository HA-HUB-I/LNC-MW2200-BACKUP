import socket
import struct
import time
import datetime
import os

HOST = "192.168.0.113"
PORT = 502
UNIT = 1
LOG_FILE = "modbus_web/discovery/discovery_history.log"

# Ranges to monitor based on app.py and common LNC maps
MONITOR_RANGES = [
    (0, 100),       # Main status and user regs
    (1000, 100),    # System info / speeds
    (6000, 300),    # CNC-PLC interface
    (8000, 200),    # System status
    (10000, 100),   # Coordinates
    (20000, 300),   # PLC registers
]

def raw_read(sock, start, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc
    try:
        sock.sendall(frame)
        resp = b""
        while len(resp) < 7:
            chunk = sock.recv(7 - len(resp))
            if not chunk: return None
            resp += chunk
        _tid, _pid, length, _uid = struct.unpack(">HHHB", resp)
        remaining = length - 1
        body = b""
        while len(body) < remaining:
            chunk = sock.recv(remaining - len(body))
            if not chunk: return None
            body += chunk
        if body[0] & 0x80: return None
        byte_count = body[1]
        return [struct.unpack(">H", body[2 + i*2:4 + i*2])[0] for i in range(byte_count // 2)]
    except:
        return None

def decode_val(addr, regs_dict):
    """Try to decode value at addr as int16, int32 (with next), and float32."""
    v1 = regs_dict.get(addr, 0)
    v2 = regs_dict.get(addr + 1, 0)
    
    # Int32 (Little Endian words - common in Modbus)
    i32_val = struct.unpack(">i", struct.pack(">HH", v2, v1))[0]
    # Float32
    try:
        f32_val = struct.unpack(">f", struct.pack(">HH", v2, v1))[0]
    except:
        f32_val = float('nan')
        
    return v1, i32_val, f32_val

def log_change(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {msg}\n"
    print(entry, end="")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

def main():
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE))
        
    print(f"Starting discovery logger on {HOST}:{PORT} (Unit {UNIT})...")
    log_change(f"--- DISCOVERY SESSION STARTED (Machine Running) ---")
    
    last_values = {}
    
    try:
        while True:
            current_values = {}
            sock = socket.create_connection((HOST, PORT), timeout=5)
            
            for start, count in MONITOR_RANGES:
                regs = raw_read(sock, start, count)
                if regs:
                    for i, v in enumerate(regs):
                        current_values[start + i] = v
                time.sleep(0.05) # Small gap between blocks
            
            sock.close()
            
            # Detect changes
            if last_values:
                changed_addrs = []
                for addr, val in current_values.items():
                    if addr in last_values and last_values[addr] != val:
                        changed_addrs.append(addr)
                
                if changed_addrs:
                    # Group changed addresses to see patterns (like 32-bit values)
                    i = 0
                    while i < len(changed_addrs):
                        addr = changed_addrs[i]
                        v1, i32, f32 = decode_val(addr, current_values)
                        prev_v1, prev_i32, prev_f32 = decode_val(addr, last_values)
                        
                        # If next address also changed, it's likely a 32-bit register
                        if i + 1 < len(changed_addrs) and changed_addrs[i+1] == addr + 1:
                            log_change(f"R{addr}-R{addr+1} (32-bit) CHANGED: "
                                       f"INT32: {prev_i32} -> {i32} (Δ{i32-prev_i32}) | "
                                       f"FLOAT32: {prev_f32:.4f} -> {f32:.4f}")
                            i += 2
                        else:
                            log_change(f"R{addr} (16-bit) CHANGED: {prev_v1} -> {v1} (Δ{v1-prev_v1})")
                            i += 1
            
            last_values = current_values
            time.sleep(0.5) # Poll frequency
            
    except KeyboardInterrupt:
        log_change("--- DISCOVERY SESSION STOPPED ---")
    except Exception as e:
        log_change(f"ERROR: {e}")

if __name__ == "__main__":
    main()
