import time
from dataclasses import dataclass, field

@dataclass
class MachineState:
    connected: bool = False
    status_word: int = 0
    x_pos: float = 0.0
    y_pos: float = 0.0
    z_pos: float = 0.0
    abs_x_pos: float = 0.0
    abs_y_pos: float = 0.0
    abs_z_pos: float = 0.0
    spindle_rpm: int = 0
    feed_rate: int = 0
    program_number: int = 0
    lot_count: int = 0
    lot_target: int = 0
    current_cycle_time_s: float = 0.0
    total_cycle_time_s: float = 0.0
    
    # Flags
    estop_active: bool = False
    alarm_active: bool = False
    cycle_running: bool = False
    feed_hold_active: bool = False
    spindle_running: bool = False
    door_open: bool = False
    vacuum_on: bool = False
    forward_pos_on: bool = False
    left_pos_on: bool = False
    right_pos_on: bool = False
    spindle_on: bool = False
    
    cnc_mode: str = "IDLE"
    cnc_mode_word: int = 0
    gcode_line: int = 0
    last_update: float = 0.0
    feed_override_pct: int = 100
    spindle_override_pct: int = 100
    
    # New Diagnostic Fields
    current_tool: int = 0
    last_m_code: int = 0
    modal_g_64_66: int = 0
    modal_group_10019: int = 0
    modal_group_10021: int = 0
    cycle_step: str = ""
    
    modal_state: dict = field(default_factory=dict)

    def decode_status_word(self) -> None:
        sw = self.status_word
        self.estop_active = bool(sw & (1 << 0))
        self.alarm_active = bool(sw & (1 << 1))
        self.cycle_running = bool(sw & (1 << 2))
        self.feed_hold_active = bool(sw & (1 << 3))
        self.spindle_running = bool(sw & (1 << 5))
        self.door_open = bool(sw & (1 << 7))

    def decode_cnc_mode(self) -> None:
        mw = self.cnc_mode_word
        _modes = {0:"MEM", 1:"MDI", 2:"ZRN", 3:"MPG", 4:"JOG", 5:"INCJOG", 6:"RAPID"}
        for bit, name in _modes.items():
            if mw & (1 << bit):
                self.cnc_mode = name
                return
        self.cnc_mode = "IDLE"
