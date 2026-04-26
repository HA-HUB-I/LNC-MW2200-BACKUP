import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("--- SCANNING FOR NON-ZERO REGISTERS (Possible Abs Coords) ---")
    
    # Скенираме основните зони
    for start in [0, 1000, 8000, 10000, 11000, 12000, 20000]:
        tid = 1
        pdu = struct.pack(">BHH", 0x03, start, 100)
        mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
        try:
            s.sendall(mbap + pdu)
            resp = s.recv(1024)
            if len(resp) < 9: continue
            bc = resp[8]
            regs = [struct.unpack(">H", resp[9+i*2:11+i*2])[0] for i in range(bc // 2)]
            
            for i, v in enumerate(regs):
                if v != 0:
                    addr = start + i
                    # Тълкуваме като signed 16-bit
                    val_s = struct.unpack(">h", struct.pack(">H", v))[0]
                    print(f"R{addr}: {val_s} ({val_s/1000.0:.3f})")
        except: continue
    s.close()

if __name__ == "__main__":
    main()
