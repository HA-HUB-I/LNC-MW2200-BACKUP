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
    print("Waiting for Cycle Running (R0 bit 2)...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    while True:
        r0 = raw_read(s, 0, 1)
        if r0 and (r0[0] & (1 << 2)):
            print("Cycle started! Scanning for moving values...")
            break
        time.sleep(0.5)
    
    # Snapshot of all non-zero
    known = {}
    for start in range(0, 15001, 100):
        regs = raw_read(s, start, 100)
        if regs:
            for i, v in enumerate(regs):
                if v != 0: known[start+i] = v
        time.sleep(0.01)
        
    print(f"Initial scan done ({len(known)} non-zero). Waiting 5 seconds...")
    time.sleep(5)
    
    print("Second scan for changes...")
    for start in range(0, 15001, 100):
        regs = raw_read(s, start, 100)
        if regs:
            for i, v in enumerate(regs):
                addr = start+i
                curr = v
                prev = known.get(addr, 0)
                if curr != prev:
                    print(f"R{addr}: {prev} -> {curr} (Δ{curr-prev})")
        time.sleep(0.01)
    
    s.close()

if __name__ == "__main__":
    main()
