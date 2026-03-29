"""
find_coords.py – Live register delta scan to locate axis positions,
vacuum coil feedback, and stopper (forward/left) status registers.

Usage:
  python find_coords.py              # position scan (move machine during prompt)
  python find_coords.py --coils      # show all coil / DI states
  python find_coords.py --stopper    # monitor stopper registers live
"""
import sys
import time
from pymodbus.client import ModbusTcpClient

HOST = "192.168.0.113"
PORT = 502
UNIT = 1

cli = ModbusTcpClient(host=HOST, port=PORT)
if not cli.connect():
    print("ERROR: Cannot connect to", HOST, PORT)
    sys.exit(1)
print(f"Connected to {HOST}:{PORT}")


# ── helpers ──────────────────────────────────────────────────────────────────

def read_regs(addr, count):
    rr = cli.read_holding_registers(address=addr, count=count, device_id=UNIT)
    if rr.isError():
        return None
    return rr.registers

def read_coils(addr, count):
    rr = cli.read_coils(address=addr, count=count, device_id=UNIT)
    if rr.isError():
        return None
    return rr.bits[:count]

def read_di(addr, count):
    rr = cli.read_discrete_inputs(address=addr, count=count, device_id=UNIT)
    if rr.isError():
        return None
    return rr.bits[:count]

def s16(v):
    """Interpret a 16-bit register as a signed int."""
    return v - 65536 if v > 32767 else v

def s32(lo, hi):
    """Combine lo/hi 16-bit words into a signed 32-bit int (×0.001 mm)."""
    raw = ((hi & 0xFFFF) << 16) | (lo & 0xFFFF)
    return raw - (1 << 32) if raw >= (1 << 31) else raw


# ─────────────────────────────────────────────────────────────────────────────
# MODE: --coils  – snapshot of all coil and DI states
# ─────────────────────────────────────────────────────────────────────────────

if "--coils" in sys.argv:
    print("\n── FC01 Coils 0–31 ──")
    bits = read_coils(0, 32)
    if bits:
        for i, b in enumerate(bits):
            if b:
                print(f"  Coil {i:2d} = ON  ← ACTIVE")
            else:
                print(f"  Coil {i:2d} = off")
    else:
        print("  ERROR reading coils")

    print("\n── FC02 Discrete Inputs 0–47 ──")
    di = read_di(0, 48)
    if di:
        for i, b in enumerate(di):
            if b:
                print(f"  DI {i:2d} = ON  ← ACTIVE")
    else:
        print("  ERROR reading DI")

    cli.close()
    sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# MODE: --stopper  – live monitor R20104 (cmd) and R20204 (status) + coils
# ─────────────────────────────────────────────────────────────────────────────

if "--stopper" in sys.argv:
    print("\nMonitoring stopper registers and coils for 30 seconds.")
    print("Activate FORWARD POS and LEFT POS on the machine now.\n")
    prev_coils = None
    for _ in range(60):
        # Stopper command register (HMI→PLC)
        cmd = read_regs(20104, 2)
        # Stopper status register (PLC→HMI)
        sts = read_regs(20204, 2)
        # All coils
        coils = read_coils(0, 16)

        cmd_val = s32(cmd[0], cmd[1]) if cmd else "ERR"
        sts_val = s32(sts[0], sts[1]) if sts else "ERR"
        coil_on = [i for i, b in enumerate(coils) if b] if coils else []

        if coils != prev_coils:
            print(f"[{time.strftime('%H:%M:%S')}] CMD={cmd_val}  STS={sts_val}  COILS ON={coil_on}")
            prev_coils = list(coils) if coils else None

        time.sleep(0.5)
    cli.close()
    sys.exit(0)


# ─────────────────────────────────────────────────────────────────────────────
# DEFAULT MODE: find axis position registers via delta scan during movement
# ─────────────────────────────────────────────────────────────────────────────

# Register ranges to scan – each entry is (start, count, label)
SCAN_RANGES = [
    # CNC-PLC extended area (we confirmed R6100/R6201 are live there)
    (6300, 100, "CNC-PLC ext A"),
    (6400, 100, "CNC-PLC ext B"),
    (6500, 100, "CNC-PLC ext C"),
    (6600, 100, "CNC-PLC ext D"),
    (6700, 100, "CNC-PLC ext E"),
    # Mid-range not yet scanned
    (2000, 100, "R2000 range"),
    (3000, 100, "R3000 range"),
    (4000, 100, "R4000 range"),
    (5000, 100, "R5000 range"),  # includes diagnostic area
    # Extended position area sometimes used by LNC
    (9500,  50, "R9500 range"),
    (9900,  50, "R9900 range"),
    # Also re-check known velocity area with wider window
    (1000,  20, "R1000 area"),
]

print("\nTaking BASELINE snapshot across", sum(c for _, c, _ in SCAN_RANGES), "registers…")
baseline = {}
for start, count, label in SCAN_RANGES:
    regs = read_regs(start, count)
    if regs:
        for i, v in enumerate(regs):
            baseline[start + i] = v

print(f"Baseline: {len(baseline)} registers captured.")
print("\n*** MOVE THE MACHINE ON Y AXIS NOW (JOG for 5 seconds) ***")
input("Press ENTER when ready to start scanning…")

# Collect multiple delta snapshots
PASSES = 3
all_changed: dict[int, list[int]] = {}

for p in range(PASSES):
    print(f"\nPass {p+1}/{PASSES} – keep moving Y…")
    time.sleep(1.5)
    for start, count, label in SCAN_RANGES:
        regs = read_regs(start, count)
        if not regs:
            continue
        for i, v in enumerate(regs):
            addr = start + i
            base = baseline.get(addr, 0)
            if abs(v - base) > 5 or (v == 0 and base != 0) or (v != 0 and base == 0):
                if addr not in all_changed:
                    all_changed[addr] = [base]
                all_changed[addr].append(v)

print(f"\nPass 4/{PASSES+1} – STOP machine, wait for settle…")
time.sleep(3)
for start, count, label in SCAN_RANGES:
    regs = read_regs(start, count)
    if not regs:
        continue
    for i, v in enumerate(regs):
        addr = start + i
        if addr in all_changed:
            all_changed[addr].append(v)

# ── Report ────────────────────────────────────────────────────────────────────
print("\n" + "═" * 60)
print("CHANGED REGISTERS (sorted by address):")
print("═" * 60)
print(f"{'Addr':>6}  {'Base':>7}  {'Values during move':40}  Notes")
print("-" * 80)

for addr in sorted(all_changed):
    vals = all_changed[addr]
    base = vals[0]
    moved_vals = vals[1:]
    note = ""

    # Try to interpret as signed 32-bit position pair with next register
    if addr + 1 in all_changed:
        next_vals = all_changed[addr + 1]
        if len(next_vals) >= 2:
            pos_mm = s32(moved_vals[0], next_vals[1]) / 1000.0
            note = f"← 32-bit pair: {pos_mm:.3f} mm?"

    # Signed 16-bit
    sv = s16(moved_vals[-1]) if moved_vals else 0
    print(f"  R{addr:<5} base={base:>7}  vals={str(moved_vals[:6]):40}  {note}")

if not all_changed:
    print("  No changing registers found in scanned ranges.")
    print("  → The controller may require Eth_ModbusServerTCP.ini [Register] mapping.")
    print("  → Try scanning R6000–R6300 (already confirmed live area) with --verbose.")

print("\n── Also checking confirmed live registers ──")
mode_r = read_regs(6201, 1)
vel_r  = read_regs(1004, 1)
print(f"  R6201 (mode) = {mode_r[0] if mode_r else 'ERR'}")
print(f"  R1004 (velocity) = {vel_r[0] if vel_r else 'ERR'}")

cli.close()
print("\nDone.")
