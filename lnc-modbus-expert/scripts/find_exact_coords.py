import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Търсим тези стойности (0.001 mm мащаб)
TARGETS = [-2167, 63369, 12143, 24141]

def raw_read(sock, start, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc
    try:
        sock.sendall(frame)
        resp = b""
        while len(resp) < 9:
            chunk = sock.recv(1)
            if not chunk: break
            resp += chunk
        if len(resp) < 9: return None
        bc = resp[8]
        data = b""
        while len(data) < bc:
            chunk = sock.recv(bc - len(data))
            if not chunk: break
            data += chunk
        return [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(bc // 2)]
    except:
        return None

def main():
    print(f"Searching for X(-2167), Y(12143), Z(24141)...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # Скенираме основните зони
    ranges = [0, 1000, 6000, 8000, 10000, 11000, 12000, 20000]
    
    for start in ranges:
        regs = raw_read(s, start, 100)
        if regs:
            for i, v in enumerate(regs):
                addr = start + i
                # Проверка за 16-битово съвпадение
                if v in TARGETS:
                    print(f"FOUND 16-bit match at R{addr}: {v}")
                
                # Проверка за 32-битово съвпадение (lo/hi)
                if i < len(regs) - 1:
                    v32 = (regs[i+1] << 16) | regs[i]
                    # Тълкуваме като signed 32-bit
                    v32_s = struct.unpack(">i", struct.pack(">I", v32 & 0xFFFFFFFF))[0]
                    if v32_s in TARGETS:
                        print(f"FOUND 32-bit match at R{addr}-R{addr+1}: {v32_s}")
    
    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
