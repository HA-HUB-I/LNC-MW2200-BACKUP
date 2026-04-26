import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Търсим Rail X: 1416.208
# Възможни мащаби: 1:1 (1416), 1:10 (14162), 1:100 (141620), 1:1000 (1416208)
TARGETS = [1416, 14162, 141620, 1416208]

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
    print("Searching for Rail X (1416.208) in all formats...")
    
    for start in [0, 1000, 8000, 10000, 11000, 12000, 20000]:
        regs = raw_read(s, start, 100)
        if regs:
            for i in range(len(regs)):
                addr = start + i
                val16 = regs[i]
                if val16 in TARGETS: print(f"FOUND 16-bit match at R{addr}: {val16}")
                
                if i < len(regs)-1:
                    v32 = (regs[i+1] << 16) | regs[i]
                    if v32 in TARGETS: print(f"FOUND 32-bit match at R{addr}: {v32}")
    s.close()

if __name__ == "__main__":
    main()
