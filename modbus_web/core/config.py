import os

MODBUS_HOST = "192.168.0.113"
MODBUS_PORT = 502
MODBUS_UNIT = 1 
POLL_INTERVAL = 0.5

# ПОТВЪРДЕНИ МАШИННИ АДРЕСИ (Machine / Relative)
R_MACHINE_X = 11570
R_MACHINE_Y = 11565
R_MACHINE_Z = 11560

# ПОТВЪРДЕНИ АБСОЛЮТНИ АДРЕСИ (Absolute / Work G54)
# Открити чрез диагностичния лог на 26.04.2026
R_ABS_X = 12032
R_ABS_Y = 12038
R_ABS_Z = 12034

# СИСТЕМНИ
R_STATUS = 0
R_SPEEDS = 1000
R_COORDS_BLOCK = 11560 # Начало на координатен блок
R_COORD_COUNT = 90     # Достатъчно да включи R11638
R_ABS_BLOCK = 12000    # Начало на абсолютен блок
R_ABS_COUNT = 50

# COILS
C_START = 0
C_HOLD = 1
C_RESET = 2
C_VACUUM = 12
C_ESTOP = 6

# DIAGNOSTIC WATCH LIST
DIAGNOSTIC_WATCH_LIST = [11560, 11565, 11570, 12032, 12034, 12038, 1007, 11638]
