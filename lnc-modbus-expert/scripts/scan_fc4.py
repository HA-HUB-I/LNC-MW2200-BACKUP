import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

def raw_read_fc4(sock, start, count, unit):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x04, start, count) # FC04
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
    print(f"Scanning Input Registers (FC04) 0-2000 for changes...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    last_snapshot = {}
    for start in range(0, 2001, 100):
        regs = raw_read_fc4(s, start, 100, UNIT)
        if regs:
            for i, v in enumerate(regs):
                if v != 0:
                    last_snapshot[start + i] = v
        time.sleep(0.01)

    print(f"Found {len(last_snapshot)} non-zero input registers. Waiting 5 seconds...")
    time.sleep(5)
    
    changes = []
    for start in range(0, 2001, 100):
        regs = raw_read_fc4(s, start, 100, UNIT)
        if regs:
            for i, v in enumerate(regs):
                addr = start + i
                prev = last_snapshot.get(addr, 0)
                if v != prev:
                    changes.append((addr, prev, v))
        time.sleep(0.01)
    
    s.close()
    
    if not changes:
        print("No changes in FC04 registers.")
    else:
        print(f"Detected {len(changes)} changed FC04 registers:")
        for addr, prev, curr in changes:
            print(f"IR{addr}: {prev} -> {curr}")

if __name__ == "__main__":
    main()
