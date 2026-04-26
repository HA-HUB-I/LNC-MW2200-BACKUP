# LNC MW2200A – Verified Modbus Map

This file contains the **STRICTLY VERIFIED** Modbus TCP register map for the LNC MW2200A CNC machine. 
Do not use any other registers for these functions without explicit verification.

## Connection
- **Port:** 502
- **Unit ID:** 1 (Required for stability and diagnostic data)
- **RegisterMode:** -32 (PLC data is offset by 32 in Modbus)

## Verified Machine Registers (Relative/Machine)
*These match the primary display on the machine.*
- **X Axis:** `R11570` (Int16, Scale: 0.001 mm)
- **Y Axis:** `R11565` (Int16, Scale: 0.001 mm)
- **Z Axis:** `R11560` (Int16, Scale: 0.001 mm)

## Verified Absolute Registers (Work G54)
*These match the Absolute/Work display.*
- **X Axis:** `R12032` (Int16, Scale: 0.001 mm)
- **Y Axis:** `R12038` (Int16, Scale: 0.001 mm)
- **Z Axis:** `R12034` (Int16, Scale: 0.001 mm)

## Speeds & Status
- **Feed Rate (Actual):** `R11638` (Int16, mm/min)
- **Spindle RPM (Actual):** `R1007` (Int16)
- **Machine Status Word:** `R0`
  - Bit 0: E-Stop
  - Bit 1: Alarm
  - Bit 2: Cycle Running
  - Bit 3: Feed Hold
  - Bit 5: Spindle Running
- **CNC Mode:** `R6201` (Bits: 0:MEM/AUTO, 1:MDI, 2:ZRN, 3:MPG, 4:JOG, 5:INCJOG)

## IO Coils (FC01)
- **Coil 12:** Vacuum Pump
- **Coils 14/18:** Forward Pos Stopper
- **Coils 15/19:** Left Pos Stopper
- **Coils 16/20:** Right Pos Stopper
- **Coils 35/36:** Dust Cover
- **Coils 7/8/3:** Spindle Motor

## Internal Logic (Diagnostic)
- **R10032 (ASCII):** Modal State A (e.g., 65='A', 66='B' running, 68='D' done).
- **R10034 (Int):** Logic Step. Transitions (e.g., 4->0->1->2) indicate tool changes or buffer prep.
- **R10006:** G-Code Modal Group (64 = G64 Constant Velocity).
- **R10019:** Operation Complete Flag (Turns to 4, then 0 at end of program).
- **R10003:** Command Type (71='G', 77='M', 84='T').
