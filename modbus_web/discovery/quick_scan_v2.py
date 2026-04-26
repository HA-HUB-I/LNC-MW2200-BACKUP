import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1 # We'll try both 0 and 1

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

def scan_range(sock, unit, start_addr, count):
    results = {}
    for addr in range(start_addr, start_addr + count, 50):
        c = min(50, start_addr + count - addr)
        r = raw_read(sock, addr, c, unit)
        if r:
            for i, v in enumerate(r):
                results[addr + i] = v
    return results

def main():
    ranges = [(0, 150), (1000, 100), (8000, 200), (10000, 50)]
    
    for unit in [0, 1]:
        print(f"\n--- SCANNING UNIT {unit} ---")
        s = socket.create_connection((HOST, PORT), timeout=5)
        
        regs1 = {}
        for start, count in ranges:
            regs1.update(scan_range(s, unit, start, count))
            
        print("Wait 3 seconds...")
        time.sleep(3)
        
        regs2 = {}
        for start, count in ranges:
            regs2.update(scan_range(s, unit, start, count))
        
        s.close()
        
        print(f"{'Addr':<6} {'Val1':<6} {'Val2':<6} {'Delta':<6}")
        print("-" * 30)
        for addr in sorted(regs1.keys()):
            v1 = regs1[addr]
            v2 = regs2.get(addr, v1)
            if v1 != 0 or v2 != 0:
                delta = v2 - v1
                if delta != 0 or v1 != 0:
                    delta_str = f"{delta:+d}" if delta != 0 else ""
                    print(f"R{addr:<5} {v1:<6} {v2:<6} {delta_str}")

if __name__ == "__main__":
    main()
