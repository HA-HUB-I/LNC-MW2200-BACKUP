import socket
import struct

HOST = "192.168.0.113"
PORT = 502

# Търсените стойности
TARGET_X = 10187
TARGET_Y = 12149
TARGET_Z = 3882

def search_unit(unit):
    print(f"\n--- SCANNING UNIT {unit} ---")
    s = socket.create_connection((HOST, PORT), timeout=5)
    found = []
    
    # Скенираме всичко до 20000 на стъпки от 100
    for start in range(0, 20001, 100):
        tid = 1
        pdu = struct.pack(">BHH", 0x03, start, 100)
        mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit)
        try:
            s.sendall(mbap + pdu)
            resp = s.recv(1024)
            if len(resp) < 9: continue
            bc = resp[8]
            data = resp[9:9+bc]
            regs = [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(len(data) // 2)]
            
            for i, v in enumerate(regs):
                addr = start + i
                val_16 = struct.unpack(">h", struct.pack(">H", v))[0]
                
                if val_16 == TARGET_X: print(f"FOUND X (10187) at R{addr}")
                if val_16 == TARGET_Y: print(f"FOUND Y (12149) at R{addr}")
                if val_16 == TARGET_Z: print(f"FOUND Z (3882) at R{addr}")
                
                # Проверка за 32-битови (Lo/Hi)
                if i < len(regs) - 1:
                    v32 = (regs[i+1] << 16) | regs[i]
                    v32_s = struct.unpack(">i", struct.pack(">I", v32 & 0xFFFFFFFF))[0]
                    if v32_s == TARGET_X: print(f"FOUND 32-bit X (10187) at R{addr}")
                    if v32_s == TARGET_Y: print(f"FOUND 32-bit Y (12149) at R{addr}")
                    if v32_s == TARGET_Z: print(f"FOUND 32-bit Z (3882) at R{addr}")
        except: continue
    s.close()

def main():
    search_unit(0)
    search_unit(1)

if __name__ == "__main__":
    main()
