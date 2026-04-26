import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Вече потвърден адрес (Machine Y)
REF_ADDR = 11565

def raw_read(sock, start, count):
    tid = 1
    pdu = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
    try:
        sock.sendall(mbap + pdu)
        resp = sock.recv(2048)
        if len(resp) < 9: return None
        bc = resp[8]
        return [struct.unpack(">H", resp[9+i*2:11+i*2])[0] for i in range(bc // 2)]
    except: return None

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("--- DELTA HUNTER (SYNC SEARCH) ---")
    
    def get_snapshot():
        data = {}
        # Скенираме зоната около потвърдения Absolute Z (R12034)
        for start in [12000, 12050, 12100, 11500, 11600]:
            r = raw_read(s, start, 50)
            if r:
                for i, v in enumerate(r): data[start+i] = v
        return data

    print("1. Taking baseline. DO NOT MOVE yet...")
    base = get_snapshot()
    
    print("2. PLEASE MOVE 'Y' AXIS NOW (JOG) for about 5-10 mm...")
    print("Waiting 10 seconds for movement...")
    time.sleep(10)
    
    print("3. Taking second snapshot...")
    curr = get_snapshot()
    s.close()

    if REF_ADDR not in curr:
        print("Error reading reference register.")
        return

    # Каква е делтата на Machine Y
    v1 = struct.unpack(">h", struct.pack(">H", base[REF_ADDR]))[0]
    v2 = struct.unpack(">h", struct.pack(">H", curr[REF_ADDR]))[0]
    ref_delta = v2 - v1

    print(f"\nREFERENCE (Machine Y) moved by: {ref_delta} units ({ref_delta/1000.0:.3f} mm)")
    print("--- SEARCHING FOR MATCHING DELTAS ---")

    for addr in sorted(base.keys()):
        if addr == REF_ADDR: continue
        
        # 16-bit delta
        b_val = struct.unpack(">h", struct.pack(">H", base[addr]))[0]
        c_val = struct.unpack(">h", struct.pack(">H", curr[addr]))[0]
        delta = c_val - b_val
        
        # 32-bit delta (Lo-Hi)
        d32 = 0
        if addr < max(base.keys()):
            b32 = struct.unpack(">i", struct.pack(">HH", base[addr+1], base[addr]))[0]
            c32 = struct.unpack(">i", struct.pack(">HH", curr[addr+1], curr[addr]))[0]
            d32 = c32 - b32

        if abs(delta) == abs(ref_delta) and abs(ref_delta) > 10:
            print(f"FOUND 16-bit SYNC at R{addr}: Delta {delta} (Current Value: {c_val/1000.0:.3f})")
        elif abs(d32) == abs(ref_delta) and abs(ref_delta) > 10:
            print(f"FOUND 32-bit SYNC at R{addr}: Delta {d32} (Current Value: {c32/1000.0:.3f})")

if __name__ == "__main__":
    main()
