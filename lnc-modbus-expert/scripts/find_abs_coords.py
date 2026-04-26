import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 0 # Използваме Unit 0, както в debug скрипта

# Търсим тези стойности
TARGET_X = -26766
TARGET_Y = 12143
TARGET_ABS_Z = 4194368

def raw_read(sock, start, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc
    try:
        sock.sendall(frame)
        resp = sock.recv(1024)
        if len(resp) < 9: return None
        bc = resp[8]
        data = resp[9:9+bc]
        return [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(len(data) // 2)]
    except:
        return None

def main():
    print(f"Searching for X({TARGET_X}), Y({TARGET_Y}), AbsZ({TARGET_ABS_Z})...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # Скенираме обхвата 11000 - 13000
    for start in range(11000, 13001, 100):
        regs = raw_read(s, start, 100)
        if regs:
            for i in range(len(regs)):
                addr = start + i
                # 16-bit check
                val_16 = struct.unpack(">h", struct.pack(">H", regs[i]))[0]
                if val_16 == TARGET_X: print(f"FOUND X match at R{addr}")
                if val_16 == TARGET_Y: print(f"FOUND Y match at R{addr}")
                
                # 32-bit check (Standard LNC order: Lo/Hi)
                if i < len(regs) - 1:
                    v32 = (regs[i+1] << 16) | regs[i]
                    v32_s = struct.unpack(">i", struct.pack(">I", v32 & 0xFFFFFFFF))[0]
                    if v32_s == TARGET_X: print(f"FOUND 32-bit X match at R{addr}")
                    if v32_s == TARGET_Y: print(f"FOUND 32-bit Y match at R{addr}")
                    if v32_s == TARGET_ABS_Z: print(f"FOUND 32-bit AbsZ match at R{addr}")

    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
