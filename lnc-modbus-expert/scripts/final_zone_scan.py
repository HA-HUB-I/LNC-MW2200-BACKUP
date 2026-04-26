import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 0

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("Deep scanning 12000-12150 and 11500-11650 for changes...")
    
    # Първи снапшот
    def get_zone():
        tid = 1
        data = {}
        for start in [11500, 12000]:
            pdu = struct.pack(">BHH", 0x03, start, 120)
            mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
            s.sendall(mbap + pdu)
            resp = s.recv(1024)
            if len(resp) > 9:
                bc = resp[8]
                regs = [struct.unpack(">H", resp[9+i*2:11+i*2])[0] for i in range(bc//2)]
                for i, v in enumerate(regs): data[start+i] = v
        return data

    snap1 = get_zone()
    print("MOVE MACHINE NOW! (X, Y, Z)...")
    time.sleep(5)
    snap2 = get_zone()
    s.close()

    print("\n--- RESULTS ---")
    for addr in sorted(snap1.keys()):
        v1 = struct.unpack(">h", struct.pack(">H", snap1[addr]))[0]
        v2 = struct.unpack(">h", struct.pack(">H", snap2[addr]))[0]
        if v1 != v2:
            print(f"R{addr}: {v1} -> {v2} (Δ{v2-v1})")

if __name__ == "__main__":
    main()
