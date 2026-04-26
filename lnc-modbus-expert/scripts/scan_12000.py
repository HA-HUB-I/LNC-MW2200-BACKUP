import socket
import struct

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
    bc = resp[8]
    data = resp[9:9+bc]
    return [struct.unpack(">H", data[i*2:i*2+2])[0] for i in range(len(data) // 2)]

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("Reading R12000-R12100 range...")
    regs = raw_read(s, 12000, 100)
    if regs:
        for i in range(0, len(regs)):
            addr = 12000 + i
            val = regs[i]
            # Signed 16-bit
            val_s = struct.unpack(">h", struct.pack(">H", val))[0]
            if abs(val_s) > 0:
                print(f"R{addr}: {val_s}")
    s.close()

if __name__ == "__main__":
    main()
