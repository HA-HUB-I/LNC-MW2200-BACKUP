import socket
import struct
import time

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

def raw_read(sock, start, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc
    sock.sendall(frame)
    resp = sock.recv(1024)
    if len(resp) < 9: return None
    byte_count = resp[8]
    return [struct.unpack(">H", resp[9 + i*2:11 + i*2])[0] for i in range(byte_count // 2)]

def main():
    print("Checking R8010-R8020 for timers...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    for _ in range(5):
        regs = raw_read(s, 8010, 10)
        if regs:
            # Combine as 32-bit to see if they look like seconds/ms
            t1 = (regs[1] << 16) | regs[0]
            t2 = (regs[3] << 16) | regs[2]
            t3 = (regs[5] << 16) | regs[4]
            print(f"R8010: {t1} | R8012: {t2} | R8014: {t3}")
        time.sleep(1)
    s.close()

if __name__ == "__main__":
    main()
