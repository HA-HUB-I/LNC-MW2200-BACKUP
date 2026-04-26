import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 0

TARGET_Z = 24141

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
    print(f"Searching for Z({TARGET_Z}) in the entire controller...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    # Скенираме всичко от 0 до 25000
    for start in range(0, 25001, 100):
        regs = raw_read(s, start, 100)
        if regs:
            for i in range(len(regs)):
                addr = start + i
                val_16 = struct.unpack(">h", struct.pack(">H", regs[i]))[0]
                if val_16 == TARGET_Z:
                    print(f"FOUND Z match at R{addr}")
                
                if i < len(regs) - 1:
                    v32 = (regs[i+1] << 16) | regs[i]
                    v32_s = struct.unpack(">i", struct.pack(">I", v32 & 0xFFFFFFFF))[0]
                    if v32_s == TARGET_Z:
                        print(f"FOUND 32-bit Z match at R{addr}")

    s.close()
    print("Search complete.")

if __name__ == "__main__":
    main()
