import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 0

TARGET_VAL = 24.141

def main():
    print(f"Searching for Z({TARGET_VAL}) as FLOAT32...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    ranges = [1000, 6000, 8000, 10000, 11000, 12000, 20000]
    
    for start in ranges:
        tid = 1
        pdu = struct.pack(">BHH", 0x03, start, 100)
        mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
        s.sendall(mbap + pdu)
        resp = s.recv(1024)
        if len(resp) < 9: continue
        data = resp[9:]
        
        for i in range(0, len(data) - 4, 2):
            # IEEE 754 Float32 (Standard)
            f_std = struct.unpack(">f", data[i:i+4])[0]
            # Swapped words
            f_swp = struct.unpack(">f", data[i+2:i+4] + data[i:i+2])[0]
            
            if round(f_std, 3) == TARGET_VAL: print(f"FOUND Float32 match at R{start + i//2}")
            if round(f_swp, 3) == TARGET_VAL: print(f"FOUND Swapped Float32 match at R{start + i//2}")

    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
