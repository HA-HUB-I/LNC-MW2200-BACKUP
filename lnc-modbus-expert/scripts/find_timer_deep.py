import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

def raw_read(sock, start, count, fc=0x03):
    tid = 1
    pdu_fc = struct.pack(">BHH", fc, start, count)
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
    print("Deep scanning for 1-second incrementing timers...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # Scanning multiple blocks to find a simple seconds counter
    blocks = [0, 500, 1000, 2000, 6000, 8000, 10000, 12000, 20000]
    
    snap1 = {}
    for b in blocks:
        regs = raw_read(s, b, 100)
        if regs:
            for i, v in enumerate(regs): snap1[b+i] = v
    
    time.sleep(2.0)
    
    snap2 = {}
    for b in blocks:
        regs = raw_read(s, b, 100)
        if regs:
            for i, v in enumerate(regs): snap2[b+i] = v
            
    s.close()
    
    print("Results (Delta 1 or 2 over 2 seconds):")
    for addr in snap1:
        v1 = snap1[addr]
        v2 = snap2.get(addr, v1)
        diff = v2 - v1
        if 1 <= diff <= 3:
            print(f"R{addr}: {v1} -> {v2} (Δ{diff})")

if __name__ == "__main__":
    main()
