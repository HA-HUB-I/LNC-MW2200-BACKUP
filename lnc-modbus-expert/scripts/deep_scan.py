import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

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
    print(f"Deep scanning registers 0-15000 for changes...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # We'll scan in chunks and keep track of non-zero values and changes
    last_snapshot = {}
    
    # Initial scan of all non-zero
    for start in range(0, 15001, 100):
        regs = raw_read(s, start, 100, UNIT)
        if regs:
            for i, v in enumerate(regs):
                if v != 0:
                    last_snapshot[start + i] = v
        time.sleep(0.01)

    print(f"Found {len(last_snapshot)} non-zero registers. Waiting 5 seconds for movement...")
    time.sleep(5)
    
    changes = []
    # Second scan only for those that were non-zero OR new non-zero
    for start in range(0, 15001, 100):
        regs = raw_read(s, start, 100, UNIT)
        if regs:
            for i, v in enumerate(regs):
                addr = start + i
                prev = last_snapshot.get(addr, 0)
                if v != prev:
                    changes.append((addr, prev, v))
        time.sleep(0.01)
    
    s.close()
    
    if not changes:
        print("No changes detected in 15000 registers over 5 seconds.")
    else:
        print(f"Detected {len(changes)} changed registers:")
        for addr, prev, curr in changes:
            delta = curr - prev
            print(f"R{addr}: {prev} -> {curr} (Δ{delta:+d})")

if __name__ == "__main__":
    main()
