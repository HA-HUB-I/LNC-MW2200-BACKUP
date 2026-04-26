import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Търсим тези големи числа (32-битови)
TARGET_ABS_X = 1289008
TARGET_ABS_Y = -283513
TARGET_RAIL_X = 1416208

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
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("Searching for 32-bit Absolute Coords...")
    
    # Скенираме обхвата 12000-12100 (където е Z) и 10000
    for start in [10000, 11500, 12000]:
        regs = raw_read(s, start, 100)
        if regs:
            for i in range(len(regs) - 1):
                addr = start + i
                # Стандартен LNC ред (Lo, Hi)
                v32 = (regs[i+1] << 16) | regs[i]
                v32_s = struct.unpack(">i", struct.pack(">I", v32 & 0xFFFFFFFF))[0]
                
                if v32_s == TARGET_ABS_X: print(f"FOUND Absolute X at R{addr}-R{addr+1}")
                if v32_s == TARGET_ABS_Y: print(f"FOUND Absolute Y at R{addr}-R{addr+1}")
                if v32_s == TARGET_RAIL_X: print(f"FOUND Rail X at R{addr}-R{addr+1}")

    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
