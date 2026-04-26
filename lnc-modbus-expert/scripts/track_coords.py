import socket
import struct
import time
import datetime

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

TARGET_REGS = [
    11565, 11570, 11633, 11638, 11933, 11938, 
    12033, 12038, 12065, 12070, 12665, 12670,
    6100, 6101, 8102, 1007, 1004
]

def raw_read(sock, addr, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, addr, count)
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
    print(f"Tracking potential coordinate registers...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # Sort for block reading if possible, but they are scattered
    # We'll just read them individually or in small groups
    
    try:
        print(f"{'Time':<12} {'R11565':>8} {'R11570':>8} {'R11633':>8} {'R11638':>8} {'R1007':>8}")
        while True:
            vals = {}
            # Read in chunks for efficiency
            # Block 11565-11640
            r1 = raw_read(s, 11565, 76)
            if r1:
                vals[11565] = r1[0]
                vals[11570] = r1[5]
                vals[11633] = r1[11633-11565]
                vals[11638] = r1[11638-11565]
            
            # Spindle
            r2 = raw_read(s, 1007, 1)
            if r2: vals[1007] = r2[0]
            
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            v_11565 = vals.get(11565, 0)
            v_11570 = vals.get(11570, 0)
            v_11633 = vals.get(11633, 0)
            v_11638 = vals.get(11638, 0)
            v_1007 = vals.get(1007, 0)
            
            print(f"{ts:<12} {v_11565:>8} {v_11570:>8} {v_11633:>8} {v_11638:>8} {v_1007:>8}")
            time.sleep(0.2)
            
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        s.close()

if __name__ == "__main__":
    main()
