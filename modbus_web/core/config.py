import os

MODBUS_HOST = "192.168.0.113"
MODBUS_PORT = 502
MODBUS_UNIT = 1 
POLL_INTERVAL = 0.5

# ПОТВЪРДЕНИ МАШИННИ АДРЕСИ (Machine Coordinates)
# На базата на Y = -32.518
R_MACHINE_Y = 11565
R_MACHINE_X = 11570
R_MACHINE_Z = 11564 # Candidate

# РАБОТНИ АДРЕСИ (Work Coordinates)
R_WORK_X = 12065
R_WORK_Y = 12038
R_WORK_Z = 12033

# СИСТЕМНИ
R_STATUS = 0
R_SPEEDS = 1000
R_COORDS = 11565 # Базов адрес за четене на блок
R_MODES = 6100
R_OVERRIDES = 8060

# COILS
C_START = 0
C_HOLD = 1
C_RESET = 2
C_VACUUM = 12
C_ESTOP = 6
