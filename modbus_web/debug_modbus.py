"""
LNC MW2200A – Read-only Modbus TCP debug probe.
SAFE: no writes, no coil commands, no machine intervention.

Usage:
    python debug_modbus.py [host] [port]

Defaults: host=192.168.0.113, port=502
"""

import socket
import struct
import sys
import time

# ---------------------------------------------------------------------------
# Try to import pymodbus; fall back to raw TCP Modbus ADU if not available
# ---------------------------------------------------------------------------
try:
    from pymodbus.client import ModbusTcpClient
    HAS_PYMODBUS = True
except ImportError:
    HAS_PYMODBUS = False
    print("[WARN] pymodbus not found – falling back to raw TCP socket.\n")

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.0.113"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 502


# ---------------------------------------------------------------------------
# Raw Modbus TCP helper (no external dependencies)
# ---------------------------------------------------------------------------
def _raw_read_holding(sock, start_addr: int, count: int, unit: int = 1):
    """Send FC03 Read Holding Registers, return list of ints or None on error."""
    tid = 1
    # MBAP header (6 bytes) + PDU (6 bytes)
    pdu = struct.pack(">BBHH", 0x03, unit, start_addr, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu) + 1, unit)
    # Re-pack correctly: MBAP = transaction_id(2) + protocol_id(2) + length(2) + unit(1)
    pdu_fc = struct.pack(">BHH", 0x03, start_addr, count)
    mbap = struct.pack(">HHHB", tid, 0, len(pdu_fc) + 1, unit)
    frame = mbap + pdu_fc

    try:
        sock.sendall(frame)
        resp = b""
        # Read MBAP (7 bytes) first
        while len(resp) < 7:
            chunk = sock.recv(7 - len(resp))
            if not chunk:
                return None
            resp += chunk
        _tid, _pid, length, _uid = struct.unpack(">HHHB", resp)
        # Read the rest (length includes the unit byte we already read)
        remaining = length - 1
        body = b""
        while len(body) < remaining:
            chunk = sock.recv(remaining - len(body))
            if not chunk:
                return None
            body += chunk
        func_code = body[0]
        if func_code & 0x80:  # exception
            print(f"  [EXCEPTION] FC={func_code & 0x7F}, code={body[1]:#04x}")
            return None
        byte_count = body[1]
        regs = []
        for i in range(byte_count // 2):
            regs.append(struct.unpack(">H", body[2 + i * 2:4 + i * 2])[0])
        return regs
    except Exception as exc:
        print(f"  [RAW ERROR] {exc}")
        return None


def _int32(lo: int, hi: int) -> int:
    raw = (hi << 16) | (lo & 0xFFFF)
    return struct.unpack(">i", struct.pack(">I", raw))[0]


def _decode_status(sw: int):
    bits = {
        0: "E-STOP",
        1: "ALARM",
        2: "CYCLE RUNNING",
        3: "FEED HOLD",
        4: "HOMING",
        5: "SPINDLE ON",
        6: "PAUSED",
        7: "DOOR OPEN",
    }
    active = [name for bit, name in bits.items() if sw & (1 << bit)]
    return active if active else ["(all bits zero – machine idle or offline)"]


# ---------------------------------------------------------------------------
# Step 1 – TCP connectivity test
# ---------------------------------------------------------------------------
print("=" * 60)
print(f"  LNC MW2200A  Modbus TCP Debug Probe")
print(f"  Target: {HOST}:{PORT}")
print("=" * 60)

print(f"\n[1] TCP connectivity test → {HOST}:{PORT} ...")
try:
    s_test = socket.create_connection((HOST, PORT), timeout=5)
    s_test.close()
    print("    ✓ TCP connection OK")
    tcp_ok = True
except Exception as e:
    print(f"    ✗ TCP FAILED: {e}")
    print("\n  ► Possible causes:")
    print("    - Wrong IP address or port")
    print("    - Controller firewall / Modbus server not enabled")
    print("    - Network / VLAN issue from this PC")
    tcp_ok = False

if not tcp_ok:
    sys.exit(1)

# ---------------------------------------------------------------------------
# Step 2 – Try multiple UNIT IDs with raw socket (safe scan)
# ---------------------------------------------------------------------------
print("\n[2] Probing unit IDs 0, 1, 255 with FC03 on registers 0–13 ...")

results_by_unit = {}
sock = socket.create_connection((HOST, PORT), timeout=5)
sock.settimeout(3)

for uid in [0, 1, 255]:
    regs = _raw_read_holding(sock, 0, 14, unit=uid)
    results_by_unit[uid] = regs
    if regs is not None:
        print(f"    Unit {uid:3d}: ✓ got {len(regs)} registers → {regs[:6]}…")
    else:
        print(f"    Unit {uid:3d}: ✗ no valid response")

sock.close()

working_units = [u for u, r in results_by_unit.items() if r is not None]
if not working_units:
    print("\n  ► No unit ID returned valid data.")
    print("    Try: python debug_modbus.py 192.168.0.113 502")
    sys.exit(1)

best_unit = working_units[0]
print(f"\n    → Using unit ID {best_unit} for further tests.")

# ---------------------------------------------------------------------------
# Step 3 – Decode main register block 0–13
# ---------------------------------------------------------------------------
print(f"\n[3] Reading main registers 0–13 (unit={best_unit}) ...")

sock = socket.create_connection((HOST, PORT), timeout=5)
sock.settimeout(3)
regs = _raw_read_holding(sock, 0, 14, unit=best_unit)

if regs is None:
    print("    ✗ Failed to read main registers.")
else:
    status_word = regs[0]
    x = _int32(regs[1], regs[2]) / 1000.0
    y = _int32(regs[3], regs[4]) / 1000.0
    z = _int32(regs[5], regs[6]) / 1000.0
    spindle = regs[7]
    feed    = regs[8]
    alarm   = regs[9]
    prog    = regs[10]
    lot_cnt = regs[11]
    lot_tgt = regs[12]
    lot_id  = regs[13]

    print(f"    Raw registers:    {regs}")
    print(f"    Status word:      {status_word:#06x}  ({status_word:016b})")
    print(f"    Status flags:     {', '.join(_decode_status(status_word))}")
    print(f"    X position:       {x:.3f} mm")
    print(f"    Y position:       {y:.3f} mm")
    print(f"    Z position:       {z:.3f} mm")
    print(f"    Spindle RPM:      {spindle}")
    print(f"    Feed rate:        {feed} mm/min")
    print(f"    Alarm code:       {alarm}")
    print(f"    Program number:   {prog}")
    print(f"    Lot count:        {lot_cnt}")
    print(f"    Lot target:       {lot_tgt}")
    print(f"    Lot ID:           {lot_id}")

# ---------------------------------------------------------------------------
# Step 4 – Diagnostic registers 5000–5008
# ---------------------------------------------------------------------------
print(f"\n[4] Reading diagnostic registers 5000–5008 ...")
diag = _raw_read_holding(sock, 5000, 9, unit=best_unit)
if diag:
    print(f"    conn_status:      {diag[0]}")
    print(f"    idle_time:        {diag[1]} s")
    print(f"    pkt_counter:      {diag[2]}")
    print(f"    err_data:         {diag[3]}")
    print(f"    err_addr:         {diag[4]}")
    print(f"    pkts_sent:        {diag[5]}")
    print(f"    pkts_received:    {diag[6]}")
    print(f"    pkts_responded:   {diag[7]}")
    print(f"    pkt_exceptions:   {diag[8]}")
else:
    print("    ✗ Diagnostic registers not available (range may not be implemented)")

# ---------------------------------------------------------------------------
# Step 5 – Absolute coordinates R10000–R10005
# ---------------------------------------------------------------------------
print(f"\n[5] Reading absolute machine coordinates R10000–R10005 ...")
abs_regs = _raw_read_holding(sock, 10000, 6, unit=best_unit)
if abs_regs:
    abs_x = _int32(abs_regs[0], abs_regs[1]) / 1000.0
    abs_y = _int32(abs_regs[2], abs_regs[3]) / 1000.0
    abs_z = _int32(abs_regs[4], abs_regs[5]) / 1000.0
    print(f"    Abs X: {abs_x:.3f} mm   Abs Y: {abs_y:.3f} mm   Abs Z: {abs_z:.3f} mm")
    print(f"    Raw: {abs_regs}")
else:
    print("    ✗ Not available (or address range not mapped)")

# ---------------------------------------------------------------------------
# Step 6 – G-code line R8102
# ---------------------------------------------------------------------------
print(f"\n[6] Reading G-code line register R8102 ...")
gc = _raw_read_holding(sock, 8102, 1, unit=best_unit)
if gc:
    print(f"    G-code line: {gc[0]}")
else:
    print("    ✗ Not available")

# ---------------------------------------------------------------------------
# Step 7 – pymodbus cross-check (if available)
# ---------------------------------------------------------------------------
if HAS_PYMODBUS:
    print(f"\n[7] Cross-check with pymodbus (unit={best_unit}) ...")
    try:
        from pymodbus.client import ModbusTcpClient
        client = ModbusTcpClient(host=HOST, port=PORT)
        connected = client.connect()
        print(f"    client.connect() → {connected}")
        if connected:
            rr = client.read_holding_registers(address=0, count=14, device_id=best_unit)
            if rr.isError():
                print(f"    ✗ pymodbus read error: {rr}")
            else:
                print(f"    ✓ pymodbus registers 0–13: {rr.registers}")
                sw = rr.registers[0]
                print(f"    Status word via pymodbus: {sw:#06x} → {_decode_status(sw)}")
        client.close()
    except Exception as exc:
        print(f"    ✗ pymodbus exception: {exc}")
else:
    print("\n[7] pymodbus not installed – skipping cross-check.")

sock.close()

# ---------------------------------------------------------------------------
# Step 8 – Live 5-second poll (read-only)
# ---------------------------------------------------------------------------
print(f"\n[8] Live 5-second read-only poll (prints every second) ...")
print("    (This is safe – no commands sent to the machine)\n")
print(f"    {'Time':>6}  {'Status':>20}  {'X mm':>9}  {'Y mm':>9}  {'Z mm':>9}  {'RPM':>6}  {'Feed':>6}")
print("    " + "-" * 75)

for i in range(5):
    try:
        sock2 = socket.create_connection((HOST, PORT), timeout=3)
        sock2.settimeout(3)
        r = _raw_read_holding(sock2, 0, 14, unit=best_unit)
        sock2.close()
        if r:
            sw = r[0]
            flags = "/".join(_decode_status(sw)[:2]) or "IDLE"
            x2 = _int32(r[1], r[2]) / 1000.0
            y2 = _int32(r[3], r[4]) / 1000.0
            z2 = _int32(r[5], r[6]) / 1000.0
            print(f"    {i+1:>6}s  {flags:>20}  {x2:>9.3f}  {y2:>9.3f}  {z2:>9.3f}  {r[7]:>6}  {r[8]:>6}")
        else:
            print(f"    {i+1:>6}s  (no data)")
    except Exception as e:
        print(f"    {i+1:>6}s  ERROR: {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("  Debug probe complete.  No commands were sent to the machine.")
print("=" * 60)
