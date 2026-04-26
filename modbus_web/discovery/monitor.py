import socket
import struct
import time
import sys

HOST = "192.168.0.113"
PORT = 502
UNIT = 0 # Testing Unit 0 as it gave Abs Z earlier

def raw_read(sock, start, count, unit):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, unit)
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
    watch_list = [
        (0, 14, "Main"),
        (32, 14, "Shifted Main"),
        (500, 20, "R500 range"),
        (532, 20, "Shifted R500"),
        (1000, 10, "R1000 range"),
        (8060, 10, "Overrides"),
        (8100, 10, "G-Code"),
        (10000, 10, "Coords"),
    ]
    
    print(f"Monitoring selected registers for 20 seconds...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    start_time = time.time()
    while time.time() - start_time < 20:
        output = []
        for start, count, label in watch_list:
            regs = raw_read(s, start, count, UNIT)
            if regs:
                output.append(f"{label}: {regs}")
            else:
                output.append(f"{label}: [ERR]")
        
        # Simple terminal "clear"
        sys.stdout.write("\033[H\033[J")
        print(f"Time: {time.time() - start_time:.1f}s")
        for line in output:
            print(line)
        
        time.sleep(1)
    
    s.close()

if __name__ == "__main__":
    main()
