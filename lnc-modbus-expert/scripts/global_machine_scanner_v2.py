import socket
import struct

HOST = "192.168.0.113"
PORT = 502

# Търсим Machine Y: -32.518
TARGET_Y = -32.518

def main():
    for unit in [0, 1]:
        print(f"\n--- SCANNING UNIT {unit} ---")
        s = socket.create_connection((HOST, PORT), timeout=3)
        
        for start in range(0, 15001, 100):
            tid = 1
            pdu = struct.pack(">BHH", 0x03, start, 100)
            mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit)
            try:
                s.sendall(mbap + pdu)
                resp = s.recv(2048)
                if len(resp) < 9: continue
                data = resp[9:]
                
                for i in range(0, len(data) - 1, 2):
                    addr = start + i//2
                    # 1. Check 16-bit
                    v16 = struct.unpack(">h", data[i:i+2])[0]
                    if abs(v16/1000.0 - TARGET_Y) < 0.005:
                        print(f"FOUND 16-bit Y match at R{addr}: {v16/1000.0:.3f}")
                    
                    # 2. Check 32-bit (Standard Lo-Hi)
                    if i < len(data) - 3:
                        v32 = struct.unpack(">i", data[i:i+2] + data[i+2:i+4])[0] # Swapped for LNC
                        if abs(v32/1000.0 - TARGET_Y) < 0.005:
                            print(f"FOUND 32-bit Y match at R{addr}")
                        
                        # 3. Check Float32
                        f32 = struct.unpack(">f", data[i:i+4])[0]
                        if abs(f32 - TARGET_Y) < 0.01:
                            print(f"FOUND Float32 Y match at R{addr}: {f32:.3f}")
            except: continue
        s.close()

if __name__ == "__main__":
    main()
