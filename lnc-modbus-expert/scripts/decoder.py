import struct

def decode(v_lo, v_hi):
    # Combine as 32-bit
    i32_val = struct.unpack(">i", struct.pack(">HH", v_hi, v_lo))[0]
    f32_val = struct.unpack(">f", struct.pack(">HH", v_hi, v_lo))[0]
    # Swapped
    i32_sw = struct.unpack(">i", struct.pack(">HH", v_lo, v_hi))[0]
    f32_sw = struct.unpack(">f", struct.pack(">HH", v_lo, v_hi))[0]
    
    return i32_val, f32_val, i32_sw, f32_sw

# Example from log:
# R11565: 37102 -> 33689
# R11570: 25608 -> 25895

print(f"{'Type':<15} {'Value 1':<20} {'Value 2':<20}")
print("-" * 55)

v1_lo, v1_hi = 37102, 25608
v2_lo, v2_hi = 33689, 25895

i32_1, f32_1, i32_sw1, f32_sw1 = decode(v1_lo, v1_hi)
i32_2, f32_2, i32_sw2, f32_sw2 = decode(v2_lo, v2_hi)

print(f"{'INT32':<15} {i32_1:<20} {i32_2:<20}")
print(f"{'FLOAT32':<15} {f32_1:<20.4f} {f32_2:<20.4f}")
print(f"{'INT32_SW':<15} {i32_sw1:<20} {i32_sw2:<20}")
print(f"{'FLOAT32_SW':<15} {f32_sw1:<20.4f} {f32_sw2:<20.4f}")
