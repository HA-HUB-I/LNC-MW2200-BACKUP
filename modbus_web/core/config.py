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

# DIAGNOSTIC WATCH LIST (Real-time logging to CSV)
DIAGNOSTIC_WATCH_LIST = [
    11560, 11561, 11562, 11563, 11564, 11565, 11566, 11567, 11568, 11569, # Machine Zone Start
    11570, 11571, 11572, 11573, 11574, 11575, 11576, 11577, 11578, 11579, # Machine Zone End
    12030, 12031, 12032, 12033, 12034, 12035, 12036, 12037, 12038, 12039, # Absolute Zone
    1007, 11638, 0 # Speeds & Status
]
