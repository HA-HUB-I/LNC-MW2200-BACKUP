import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("--- MACHINE COORD BLOCK (11560-11580) ---")
    
    tid = 1
    pdu = struct.pack(">BHH", 0x03, 11560, 21)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, UNIT)
    s.sendall(mbap + pdu)
    resp = s.recv(1024)
    if len(resp) > 9:
        bc = resp[8]
        data = resp[9:9+bc]
        regs = [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(bc//2)]
        
        for i, v in enumerate(regs):
            addr = 11560 + i
            val_s = struct.unpack(">h", struct.pack(">H", v))[0]
            print(f"R{addr}: {val_s} ({val_s/1000.0:.3f})")
            
    s.close()

if __name__ == "__main__":
    main()
