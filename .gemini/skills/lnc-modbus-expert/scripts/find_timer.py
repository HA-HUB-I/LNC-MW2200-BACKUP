import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

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

def main():
    print("Searching for incrementing timers (0.5s interval)...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    ranges = [(500, 100), (1000, 100), (8000, 100), (11500, 100)]
    
    snapshots = []
    for _ in range(3):
        snap = {}
        for start, count in ranges:
            regs = raw_read(s, start, count)
            if regs:
                for i, v in enumerate(regs):
                    snap[start + i] = v
        snapshots.append(snap)
        time.sleep(1.0)
    
    s.close()
    
    print("Checking for values that increased by ~1 or ~1000 per second...")
    for addr in snapshots[0].keys():
        v1 = snapshots[0][addr]
        v2 = snapshots[1][addr]
        v3 = snapshots[2][addr]
        
        diff1 = v2 - v1
        diff2 = v3 - v2
        
        if diff1 > 0 and diff1 == diff2:
            # Possible timer
            print(f"R{addr}: {v1} -> {v2} -> {v3} (Delta: {diff1})")

if __name__ == "__main__":
    main()
