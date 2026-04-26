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
    try:
        sock.sendall(frame)
        resp = b""
        while len(resp) < 7:
            chunk = sock.recv(7 - len(resp))
            if not chunk: return None
            resp += chunk
        _tid, _pid, length, _uid = struct.unpack(">HHHB", resp)
        remaining = length - 1
        body = b""
        while len(body) < remaining:
            chunk = sock.recv(remaining - len(body))
            if not chunk: return None
            body += chunk
        if body[0] & 0x80: return None
        byte_count = body[1]
        return [struct.unpack(">H", body[2 + i*2:4 + i*2])[0] for i in range(byte_count // 2)]
    except:
        return None

def main():
    s = socket.create_connection((HOST, PORT), timeout=5)
    print("Logging R500-R600 and R1100-R1200 for 10 seconds...")
    
    for t in range(10):
        r500 = raw_read(s, 500, 20)
        r1100 = raw_read(s, 1100, 20)
        print(f"T={t}s | R500: {r500[:5]}... | R1100: {r1100[:5]}...")
        time.sleep(1.0)
    
    s.close()

if __name__ == "__main__":
    main()
