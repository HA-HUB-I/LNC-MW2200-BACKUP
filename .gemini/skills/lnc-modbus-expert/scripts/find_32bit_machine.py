import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Търсим тези големи числа (32-битови)
TARGETS = {
    "Abs X (1289.008)": 1289008,
    "Abs Y (-283.513)": -283513,
    "Rail X (1416.208)": 1416208
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
    print("Searching for 32-bit Machine/Rail Coordinates...")
    
    # Скенираме всички важни обхвати
    for start in [0, 1000, 8000, 10000, 11000, 12000, 20000]:
        regs = raw_read(s, start, 100)
        if regs:
            for i in range(len(regs) - 1):
                addr = start + i
                # Пробваме двата варианта на подредба на байтовете (Lo/Hi и Hi/Lo)
                v32_lo_hi = struct.unpack(">i", struct.pack(">HH", regs[i+1], regs[i]))[0]
                v32_hi_lo = struct.unpack(">i", struct.pack(">HH", regs[i], regs[i+1]))[0]
                
                for name, target in TARGETS.items():
                    if v32_lo_hi == target: print(f"MATCH {name}: FOUND at R{addr} (Lo-Hi)")
                    if v32_hi_lo == target: print(f"MATCH {name}: FOUND at R{addr} (Hi-Lo)")

    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
