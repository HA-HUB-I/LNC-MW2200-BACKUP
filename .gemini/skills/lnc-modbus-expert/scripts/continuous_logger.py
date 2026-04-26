import socket
import struct
import time
import datetime
import csv
import os

HOST = "192.168.0.113"
PORT = 502
UNIT = 1 # We'll stick with 1 as it's the most common and worked before

LOG_FILE = "modbus_web/discovery/changes.csv"

def raw_read(sock, start, count, unit):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, unit)
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

def main():
    if not os.path.exists(os.path.dirname(LOG_FILE)):
        os.makedirs(os.path.dirname(LOG_FILE))
        
    print(f"Continuous change logger started. Target: {HOST}:{PORT}")
    
    # 1. Identify all non-zero registers initially
    s = socket.create_connection((HOST, PORT), timeout=5)
    known_regs = {}
    print("Scanning for non-zero registers...")
    for start in range(0, 15001, 100):
        regs = raw_read(s, start, 100, UNIT)
        if regs:
            for i, v in enumerate(regs):
                addr = start + i
                if v != 0:
                    known_regs[addr] = v
        time.sleep(0.01)
    
    print(f"Initial scan complete. Found {len(known_regs)} non-zero registers.")
    
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Address", "OldValue", "NewValue", "Delta"])
        
        try:
            while True:
                # We'll only poll the known non-zero registers and a few critical ranges
                ranges_to_poll = set()
                for addr in known_regs:
                    ranges_to_poll.add((addr // 100) * 100)
                
                # Add some critical ranges regardless
                ranges_to_poll.add(0)
                ranges_to_poll.add(1000)
                ranges_to_poll.add(8000)
                ranges_to_poll.add(10000)
                
                for start in sorted(ranges_to_poll):
                    regs = raw_read(s, start, 100, UNIT)
                    if regs:
                        for i, v in enumerate(regs):
                            addr = start + i
                            prev = known_regs.get(addr, 0)
                            if v != prev:
                                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                delta = v - prev
                                writer.writerow([timestamp, addr, prev, v, delta])
                                f.flush()
                                print(f"[{timestamp}] R{addr}: {prev} -> {v} (Δ{delta})")
                                known_regs[addr] = v
                    time.sleep(0.01)
                
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("Stopped.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            s.close()

if __name__ == "__main__":
    main()
