import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1 # Използваме Unit 1, както в работещия app.py

# ПОТВЪРДЕНИ РЕГИСТРИ
REF_X = 11565
REF_Y = 11570

def raw_read(sock, start, count):
    tid = 1
    pdu = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
    try:
        sock.sendall(mbap + pdu)
        resp = sock.recv(1024)
        if len(resp) < 9: return None
        bc = resp[8]
        return [struct.unpack(">H", resp[9+i*2:11+i*2])[0] for i in range(bc // 2)]
    except: return None

def main():
    s = socket.create_connection((HOST, PORT), timeout=2)
    print("--- ABSOLUTE COORDINATE HUNTER (READ-ONLY) ---")
    
    # 1. Начално състояние
    def snap():
        data = {}
        # Скенираме широки зони, където може да са Absolute
        for start in [10000, 11500, 12000, 12500]:
            r = raw_read(s, start, 100)
            if r:
                for i, v in enumerate(r): data[start+i] = v
        return data

    print("Taking baseline...")
    base = snap()
    
    print("PLEASE MOVE X and Y NOW (JOG)... Waiting 10s...")
    time.sleep(10)
    
    print("Taking new snapshot...")
    curr = snap()
    s.close()

    if REF_X not in curr or REF_Y not in curr:
        print("Error: Could not read reference registers. Try again.")
        return

    # Изчисляваме с колко са се мръднали потвърдените регистри
    dx = struct.unpack(">h", struct.pack(">H", curr[REF_X]))[0] - struct.unpack(">h", struct.pack(">H", base[REF_X]))[0]
    dy = struct.unpack(">h", struct.pack(">H", curr[REF_Y]))[0] - struct.unpack(">h", struct.pack(">H", base[REF_Y]))[0]

    print(f"\nMovement detected: Delta X = {dx}, Delta Y = {dy}")
    print("Searching for other registers with the SAME delta...")

    for addr in sorted(base.keys()):
        if addr in [REF_X, REF_Y]: continue
        
        v1 = struct.unpack(">h", struct.pack(">H", base[addr]))[0]
        v2 = struct.unpack(">h", struct.pack(">H", curr[addr]))[0]
        diff = v2 - v1
        
        if diff != 0:
            if abs(diff) == abs(dx) and dx != 0:
                print(f"FOUND MATCH FOR X: R{addr} (Value: {v2/1000.0:.3f} mm)")
            elif abs(diff) == abs(dy) and dy != 0:
                print(f"FOUND MATCH FOR Y: R{addr} (Value: {v2/1000.0:.3f} mm)")
            elif abs(diff) > 2: # Всичко друго, което се движи
                print(f"R{addr} moved: {v1} -> {v2} (Delta: {diff})")

if __name__ == "__main__":
    main()
