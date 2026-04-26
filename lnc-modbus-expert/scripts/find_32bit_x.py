import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Търсим тези големи числа
# 1. 1416.208 (Rail X) -> 1416208
# 2. 1289.008 (Abs X) -> 1289008
TARGETS = {
    "Rail X": 1416208,
    "Abs X": 1289008
}

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
    print("Searching for 32-bit X coordinates (1416.208 and 1289.008)...")
    
    # Скенираме всичко от 0 до 20000
    for start in range(0, 20001, 100):
        regs = raw_read(s, start, 100)
        if regs:
            for i in range(len(regs) - 1):
                addr = start + i
                # Пробваме двата варианта на подредба (Standard vs Swapped)
                v32_std = (regs[i+1] << 16) | regs[i]
                v32_swp = (regs[i] << 16) | regs[i+1]
                
                # Тълкуваме като signed
                val_std = struct.unpack(">i", struct.pack(">I", v32_std & 0xFFFFFFFF))[0]
                val_swp = struct.unpack(">i", struct.pack(">I", v32_swp & 0xFFFFFFFF))[0]

                for name, target in TARGETS.items():
                    # Търсим с малък толеранс (ако се е мръднала малко)
                    if abs(val_std - target) < 10: print(f"FOUND {name} (Std) at R{addr}")
                    if abs(val_swp - target) < 10: print(f"FOUND {name} (Swp) at R{addr}")

    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
