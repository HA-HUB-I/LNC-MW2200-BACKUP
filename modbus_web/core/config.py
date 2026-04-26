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
R_ABS_X = 12032
R_ABS_Y = 12038
R_ABS_Z = 12034

# СИСТЕМНИ
R_STATUS = 0
R_SPEEDS = 1000
R_COORDS_BLOCK = 11560 
R_COORD_COUNT = 90     
R_ABS_BLOCK = 12000    
R_ABS_COUNT = 50

# COILS
C_START = 0
C_HOLD = 1
C_RESET = 2
C_VACUUM = 12
C_ESTOP = 6

# --- NEW DIAGNOSTIC WATCH LIST ---
# Премахваме потвърдените координати и оставяме само логическите регистри
DIAGNOSTIC_WATCH_LIST = [
    0, 32, 33, 34,         # Основен статус и неговите огледални копия
    10006, 10019, 10021,   # G-Code Модални състояния и финални флагове
    10032, 10034,          # ASCII стъпки и логически стъпки
    21001, 21002,          # M-Code буфери
    10, 11, 13,            # Програма, Инструмент, Lot ID
    6201                   # Режим (JOG/AUTO/MDI)
]
