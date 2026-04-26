import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 0

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
    s = socket.create_connection((HOST, PORT), timeout=2)
    print("SEARCHING FOR HIGH-FREQUENCY CHANGES (ACTUAL LIVE DATA)...")
    
    # Скенираме критичните зони
    ranges = [(32, 20), (1000, 20), (11500, 150), (12000, 100)]
    
    last = {}
    while True:
        try:
            for start, count in ranges:
                regs = raw_read(s, start, count)
                if regs:
                    for i, v in enumerate(regs):
                        addr = start + i
                        if addr in last and v != last[addr]:
                            # Показваме само регистри, които се променят плавно (координати)
                            diff = abs(v - last[addr])
                            if 1 <= diff < 5000:
                                print(f"[LIVE] R{addr}: {v} (Delta: {v - last[addr]})")
                        last[addr] = v
            time.sleep(0.1) # Бързо опресняване
        except KeyboardInterrupt: break
    s.close()

if __name__ == "__main__":
    main()
