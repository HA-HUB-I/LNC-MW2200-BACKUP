"""
LNC MW2200A – Register address scanner (READ-ONLY, no commands sent).
Scans multiple register ranges looking for non-zero / changing values
to identify where the controller actually maps its machine data.

Usage:
    python scan_registers.py [host] [port]
"""

import socket
import struct
import sys
import time

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.113"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 502
UNIT = 1   # try 0 if 1 returns nothing


def raw_read(sock, start: int, count: int, unit: int = UNIT):
    """FC03 Read Holding Registers. Returns list of ints or None."""
    tid = 1
    pdu_fc = struct.pack(">BHH", 0x03, start, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, unit)
    frame = mbap + pdu_fc
    try:
        sock.sendall(frame)
        resp = b""
        while len(resp) < 7:
            chunk = sock.recv(7 - len(resp))
            if not chunk:
                return None
            resp += chunk
        _tid, _pid, length, _uid = struct.unpack(">HHHB", resp)
        remaining = length - 1
        body = b""
        while len(body) < remaining:
            chunk = sock.recv(remaining - len(body))
            if not chunk:
                return None
            body += chunk
        if body[0] & 0x80:
            return None   # exception response
        byte_count = body[1]
        return [struct.unpack(">H", body[2 + i*2:4 + i*2])[0] for i in range(byte_count // 2)]
    except Exception:
        return None


def new_sock():
    s = socket.create_connection((HOST, PORT), timeout=4)
    s.settimeout(4)
    return s


def int32(lo, hi):
    raw = (hi << 16) | (lo & 0xFFFF)
    return struct.unpack(">i", struct.pack(">I", raw))[0]


print("=" * 70)
print(f"  LNC MW2200A  Register Scanner  –  READ-ONLY  –  {HOST}:{PORT}")
print("=" * 70)

# ---------------------------------------------------------------------------
# Phase A: Quick non-zero scan across key ranges
# ---------------------------------------------------------------------------
SCAN_RANGES = [
    (0,     50,   "Main status block (0–49)"),
    (100,   50,   "Block 100–149"),
    (200,   50,   "Block 200–249"),
    (500,   50,   "Block 500–549"),
    (1000,  50,   "Block 1000–1049"),
    (2000,  50,   "Block 2000–2049"),
    (3000,  50,   "Block 3000–3049"),
    (4000,  50,   "Block 4000–4049"),
    (4990,  20,   "Diagnostic vicinity 4990–5009"),
    (5000,  20,   "Diagnostic 5000–5019"),
    (6000,  50,   "Block 6000–6049"),
    (7000,  50,   "Block 7000–7049"),
    (8000,  50,   "System-status 8000–8049"),
    (8050,  50,   "System-status 8050–8099"),
    (8100,  20,   "G-code line vicinity 8100–8119"),
    (9000,  50,   "Block 9000–9049"),
    (9950,  60,   "Block 9950–10009"),
    (10000, 20,   "Abs-coord 10000–10019"),
    (10100, 20,   "Block 10100–10119"),
    (20100, 10,   "Stopper CMD 20100–20109"),
    (20200, 10,   "Stopper STS 20200–20209"),
    (30000, 50,   "Block 30000–30049"),
    (40000, 50,   "Block 40000–40049"),
]

print("\n[A] Scanning register ranges for non-zero values ...\n")
print(f"  {'Range':<30}  {'Non-zero regs'}")
print("  " + "-" * 60)

nonzero_ranges = []
for start, count, label in SCAN_RANGES:
    try:
        s = new_sock()
        regs = raw_read(s, start, count, UNIT)
        s.close()
        if regs is None:
            print(f"  {label:<30}  [exception/no response]")
            continue
        nz = [(start + i, v) for i, v in enumerate(regs) if v != 0]
        if nz:
            nz_str = "  ".join(f"R{addr}={val}({val:#06x})" for addr, val in nz[:8])
            if len(nz) > 8:
                nz_str += f"  … (+{len(nz)-8} more)"
            print(f"  {label:<30}  *** {nz_str}")
            nonzero_ranges.append((start, count, label, regs))
        else:
            print(f"  {label:<30}  (all zero)")
    except Exception as e:
        print(f"  {label:<30}  [error: {e}]")

# ---------------------------------------------------------------------------
# Phase B: Two-pass check for changing values (catch axis in motion)
# ---------------------------------------------------------------------------
print("\n[B] Two-pass delta check (2 s apart) for moving registers ...")
print("    (if machine is running, axis position registers will change)\n")

snapshot1 = {}
snapshot2 = {}

check_ranges = [
    (0, 100),
    (8000, 200),
    (10000, 20),
    (20100, 20),
    (20200, 20),
]

for start, count in check_ranges:
    try:
        s = new_sock()
        r = raw_read(s, start, count, UNIT)
        s.close()
        if r:
            for i, v in enumerate(r):
                snapshot1[start + i] = v
    except Exception:
        pass

time.sleep(2)

for start, count in check_ranges:
    try:
        s = new_sock()
        r = raw_read(s, start, count, UNIT)
        s.close()
        if r:
            for i, v in enumerate(r):
                snapshot2[start + i] = v
    except Exception:
        pass

changed = {addr: (snapshot1[addr], snapshot2[addr])
           for addr in snapshot1
           if addr in snapshot2 and snapshot1[addr] != snapshot2[addr]}

if changed:
    print("  *** CHANGING REGISTERS (machine in motion / active) ***")
    for addr, (v1, v2) in sorted(changed.items()):
        print(f"    R{addr:>6}: {v1:>6} → {v2:>6}  (delta {v2-v1:+d})")
else:
    print("  No changing registers detected in 2 s window.")
    print("  (Machine may be paused, or status registers may be at unexpected addresses)")

# ---------------------------------------------------------------------------
# Phase C: FC01 Read Coils – check discrete inputs/outputs
# ---------------------------------------------------------------------------
print("\n[C] Reading coils 0–31 (FC01) ...")
try:
    tid = 2
    pdu_fc = struct.pack(">BHH", 0x01, 0, 32)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc

    s = new_sock()
    s.sendall(frame)
    resp = b""
    while len(resp) < 7:
        chunk = s.recv(7 - len(resp))
        if not chunk:
            break
        resp += chunk
    _tid, _pid, length, _uid = struct.unpack(">HHHB", resp)
    body = b""
    remaining = length - 1
    while len(body) < remaining:
        chunk = s.recv(remaining - len(body))
        if not chunk:
            break
        body += chunk
    s.close()

    if body[0] == 0x01:
        byte_count = body[1]
        coil_bits = []
        for b in body[2:2+byte_count]:
            for bit in range(8):
                coil_bits.append((b >> bit) & 1)
        active = [i for i, v in enumerate(coil_bits) if v]
        coil_names = {
            0: "Cycle Start", 1: "Feed Hold", 2: "Reset/Alarm clear",
            3: "Spindle CW", 4: "Spindle CCW", 5: "Vacuum Pump",
            6: "E-Stop", 7: "Lot Reset", 8: "Aspiration"
        }
        print(f"  Coil bytes: {body[2:2+byte_count].hex()}")
        if active:
            print(f"  Active coils: {[(i, coil_names.get(i, f'coil{i}')) for i in active]}")
        else:
            print("  All coils = 0 (no outputs currently active)")
    else:
        print(f"  Exception response: {body.hex()}")
except Exception as e:
    print(f"  Coil read error: {e}")

# ---------------------------------------------------------------------------
# Phase D: FC02 Read Discrete Inputs 0–31
# ---------------------------------------------------------------------------
print("\n[D] Reading discrete inputs 0–31 (FC02) ...")
try:
    tid = 3
    pdu_fc = struct.pack(">BHH", 0x02, 0, 32)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, UNIT)
    frame = mbap + pdu_fc

    s = new_sock()
    s.sendall(frame)
    resp = b""
    while len(resp) < 7:
        chunk = s.recv(7 - len(resp))
        if not chunk:
            break
        resp += chunk
    _tid, _pid, length, _uid = struct.unpack(">HHHB", resp)
    body = b""
    remaining = length - 1
    while len(body) < remaining:
        chunk = s.recv(remaining - len(body))
        if not chunk:
            break
        body += chunk
    s.close()

    if body[0] == 0x02:
        byte_count = body[1]
        di_bits = []
        for b in body[2:2+byte_count]:
            for bit in range(8):
                di_bits.append((b >> bit) & 1)
        active = [i for i, v in enumerate(di_bits) if v]
        print(f"  DI bytes: {body[2:2+byte_count].hex()}")
        if active:
            print(f"  Active inputs: {active}")
        else:
            print("  All discrete inputs = 0")
    elif body[0] & 0x80:
        print(f"  Exception code: {body[1]:#04x} (FC02 may not be supported)")
    else:
        print(f"  Unexpected response: {body.hex()}")
except Exception as e:
    print(f"  Discrete input read error: {e}")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("  Scan complete. No commands were sent to the machine.")
if changed:
    print(f"  ► Found {len(changed)} changing registers – check addresses above.")
else:
    print("  ► No movement detected. Non-zero ranges listed in Phase A.")
print("=" * 70)
