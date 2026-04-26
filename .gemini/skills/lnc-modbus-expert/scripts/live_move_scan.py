import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 0

def raw_read(sock, start, count):
    tid = 1
    pdu = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
    try:
        sock.sendall(mbap + pdu)
        resp = sock.recv(1024)
        if len(resp) < 9: return None
        bc = resp[8]
        data = resp[9:9+bc]
        return [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(len(data) // 2)]
    except: return None

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("Capturing baseline...")
    
    ranges = [(10000, 100), (11500, 150), (12000, 150), (12500, 150)]
    
    def get_snap():
        snap = {}
        for start, count in ranges:
            r = raw_read(s, start, count)
            if r:
                for i, v in enumerate(r): snap[start+i] = v
        return snap

    base = get_snap()
    print("MOVE MACHINE NOW! (Press keys for X, Y, Z)...")
    
    # Следим за промени в реално време за 15 секунди
    end_time = time.time() + 15
    changed_already = set()
    
    while time.time() < end_time:
        curr = get_snap()
        for addr, val in curr.items():
            if addr in base and val != base[addr]:
                if addr not in changed_already:
                    # Тълкуваме като signed 16-bit
                    v_base = struct.unpack(">h", struct.pack(">H", base[addr]))[0]
                    v_curr = struct.unpack(">h", struct.pack(">H", val))[0]
                    print(f"R{addr} CHANGED: {v_base} -> {v_curr} (Delta: {v_curr - v_base})")
                    changed_already.add(addr)
        time.sleep(0.2)
    
    s.close()
    print("Capture finished.")

if __name__ == "__main__":
    main()
