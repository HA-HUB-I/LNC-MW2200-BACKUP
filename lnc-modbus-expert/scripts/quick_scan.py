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
    print(f"Scanning registers 0-200 on {HOST}...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # First pass
    regs1 = {}
    for start in range(0, 201, 50):
        r = raw_read(s, start, min(50, 201-start))
        if r:
            for i, v in enumerate(r):
                regs1[start + i] = v
    
    print("Wait 2 seconds for second pass...")
    time.sleep(2)
    
    # Second pass
    regs2 = {}
    for start in range(0, 201, 50):
        r = raw_read(s, start, min(50, 201-start))
        if r:
            for i, v in enumerate(r):
                regs2[start + i] = v
    
    s.close()
    
    print(f"{'Addr':<6} {'Val1':<6} {'Val2':<6} {'Delta':<6}")
    print("-" * 30)
    for addr in sorted(regs1.keys()):
        v1 = regs1[addr]
        v2 = regs2.get(addr, v1)
        if v1 != 0 or v2 != 0:
            delta = v2 - v1
            delta_str = f"{delta:+d}" if delta != 0 else ""
            print(f"R{addr:<5} {v1:<6} {v2:<6} {delta_str}")

if __name__ == "__main__":
    main()
