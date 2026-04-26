import socket
import struct

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

# Търсим Machine Y: -32.518
# В 16-битов signed формат това е -32518
# В 16-битов unsigned (Modbus raw) това е 33018
TARGET_Y = -32518

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
    print(f"Searching for Machine Y ({TARGET_Y})...")
    
    # Скенираме широки обхвати
    found_at = []
    for start in range(0, 20001, 100):
        regs = raw_read(s, start, 100)
        if regs:
            for i, v in enumerate(regs):
                # Проверка за 16-битово съвпадение (signed)
                val_16 = struct.unpack(">h", struct.pack(">H", v))[0]
                if val_16 == TARGET_Y:
                    addr = start + i
                    print(f"FOUND Y at R{addr}")
                    found_at.append(addr)
                    
                # Проверка за 32-битово съвпадение (Lo/Hi)
                if i < len(regs) - 1:
                    v32 = (regs[i+1] << 16) | regs[i]
                    v32_s = struct.unpack(">i", struct.pack(">I", v32 & 0xFFFFFFFF))[0]
                    if v32_s == TARGET_Y:
                        print(f"FOUND 32-bit Y at R{start+i}-R{start+i+1}")
    
    if found_at:
        print("\n--- NEIGHBOR ANALYSIS ---")
        for addr in found_at:
            print(f"\nRegisters around R{addr}:")
            # Четем +/- 10 регистъра около намерения адрес
            neighbors = raw_read(s, addr - 10, 21)
            if neighbors:
                for idx, val in enumerate(neighbors):
                    curr_addr = addr - 10 + idx
                    val_s = struct.unpack(">h", struct.pack(">H", val))[0]
                    mark = "<- Y" if curr_addr == addr else ""
                    print(f"R{curr_addr}: {val_s} ({val_s/1000.0:.3f}) {mark}")
    
    s.close()

if __name__ == "__main__":
    main()
