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
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    blocks = [0, 100, 500, 1000, 1100, 8000, 8100, 10000, 11500, 12000, 20000, 21000, 22000]
    
    print("Snapshot 1...")
    snap1 = {}
    for b in blocks:
        regs = raw_read(s, b, 100)
        if regs:
            for i, v in enumerate(regs): snap1[b+i] = v
            
    print("Waiting 10 seconds...")
    time.sleep(10.0)
    
    print("Snapshot 2...")
    snap2 = {}
    for b in blocks:
        regs = raw_read(s, b, 100)
        if regs:
            for i, v in enumerate(regs): snap2[b+i] = v
            
    s.close()
    
    print("\n--- DETECTED CHANGES OVER 10 SECONDS ---")
    for addr in sorted(snap1.keys()):
        v1 = snap1[addr]
        v2 = snap2.get(addr, v1)
        if v1 != v2:
            delta = v2 - v1
            # Filter out the known high-speed timers like R11570
            if addr == 11570: continue
            
            # Check if it could be a 32-bit value
            v1_32 = 0
            v2_32 = 0
            if addr % 2 == 0 and (addr+1) in snap1:
                v1_32 = (snap1[addr+1] << 16) | snap1[addr]
                v2_32 = (snap2[addr+1] << 16) | snap2[addr]
                delta_32 = v2_32 - v1_32
                print(f"R{addr}-R{addr+1} (32-bit): {v1_32} -> {v2_32} (Δ{delta_32})")
            else:
                print(f"R{addr} (16-bit): {v1} -> {v2} (Δ{delta})")

if __name__ == "__main__":
    main()
