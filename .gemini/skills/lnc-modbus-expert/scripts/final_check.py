import socket
import struct
import time
import datetime

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

def raw_read(sock, addr, count):
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, addr, count)
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
    print(f"Final discovery check...")
    s = socket.create_connection((HOST, PORT), timeout=5)
    
    try:
        print(f"{'Time':<12} {'X(R11565)':>10} {'Y(R11570)':>10} {'Z(R11575)':>10} {'Vel(R1004)':>10} {'RPM(1007)':>10} {'Line(8102)':>10}")
        for _ in range(50):
            vals = {}
            r1 = raw_read(s, 11565, 11) # Read 11565 to 11575
            if r1:
                vals['x'] = r1[0]
                vals['y'] = r1[5]
                vals['z'] = r1[10]
            
            r2 = raw_read(s, 1004, 4) # Read 1004 to 1007
            if r2:
                vals['vel'] = r2[0]
                vals['rpm'] = r2[3]
                
            r3 = raw_read(s, 8102, 1)
            if r3: vals['line'] = r3[0]
            
            ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
            print(f"{ts:<12} {vals.get('x',0):>10} {vals.get('y',0):>10} {vals.get('z',0):>10} {vals.get('vel',0):>10} {vals.get('rpm',0):>10} {vals.get('line',0):>10}")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("Stopped.")
    finally:
        s.close()

if __name__ == "__main__":
    main()
