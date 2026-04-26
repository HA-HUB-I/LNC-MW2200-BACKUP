import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 0

# Вече знаем тези "Work" регистри
WORK_X_ADDR = 12065
WORK_Y_ADDR = 12038

def raw_read(sock, start, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc
    try:
        sock.sendall(frame)
        resp = b""
        while len(resp) < 9:
            chunk = sock.recv(1)
            if not chunk: break
            resp += chunk
        bc = resp[8]
        data = b""
        while len(data) < bc:
            chunk = sock.recv(bc - len(data))
            if not chunk: break
            data += chunk
        return [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(bc // 2)]
    except:
        return None

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("--- ABSOLUTE COORD HUNTER ---")
    print("1. Taking initial snapshot of 11000-13000...")
    
    ranges = [(11000, 100), (11500, 100), (12000, 100), (12500, 100)]
    
    def get_all():
        data = {}
        for start, count in ranges:
            r = raw_read(s, start, count)
            if r:
                for i, v in enumerate(r): data[start+i] = v
        return data

    snap1 = get_all()
    print("2. PLEASE MOVE X, Y AND Z AXES NOW (JOG)...")
    print("Waiting 10 seconds for movement...")
    time.sleep(10)
    
    print("3. Taking second snapshot...")
    snap2 = get_all()
    s.close()
    
    # Търсим промяната в Work X, за да разберем колко сме преместили
    dx = struct.unpack(">h", struct.pack(">H", snap2[WORK_X_ADDR]))[0] - struct.unpack(">h", struct.pack(">H", snap1[WORK_X_ADDR]))[0]
    dy = struct.unpack(">h", struct.pack(">H", snap2[WORK_Y_ADDR]))[0] - struct.unpack(">h", struct.pack(">H", snap1[WORK_Y_ADDR]))[0]
    
    print(f"\nMovement detected: ΔX={dx}, ΔY={dy}")
    print("--- POSSIBLE ABSOLUTE REGISTERS ---")
    
    for addr in sorted(snap1.keys()):
        if addr in [WORK_X_ADDR, WORK_Y_ADDR]: continue
        
        v1 = struct.unpack(">h", struct.pack(">H", snap1[addr]))[0]
        v2 = struct.unpack(">h", struct.pack(">H", snap2[addr]))[0]
        diff = v2 - v1
        
        if diff != 0:
            match = ""
            if abs(diff) == abs(dx) and dx != 0: match = "<- MATCHES X MOVEMENT"
            if abs(diff) == abs(dy) and dy != 0: match = "<- MATCHES Y MOVEMENT"
            if match or abs(diff) > 5: # Показваме всичко, което се е мръднало
                print(f"R{addr}: {v1} -> {v2} (Δ{diff}) {match}")

if __name__ == "__main__":
    main()
