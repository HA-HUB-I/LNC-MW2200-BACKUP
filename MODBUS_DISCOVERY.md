# LNC MW2200A – Modbus Discovery Log & Next-Session Guide

> Последна актуализация: 2026-03-29  
> Машина: 192.168.0.113:502 · Unit ID 1 · Dashboard: http://localhost:5000

---

## ✅ ПОТВЪРДЕНИ РЕГИСТРИ (live debug)

| Регистър | Стойност/Кодиране | Функция | Бележка |
|---|---|---|---|
| **R1004** | 0–15000 mm/min | Моментална скорост на активната ос | 0 когато ос не се движи |
| **R1007** | 0–24000 RPM | Живата скорост на шпиндела | 18000 по време на работа |
| **R6100** | bit flags | CNC статус/lamp word | Режимни индикатори |
| **R6201** | bit flags | CNC mode word | bit0=MEM, bit1=MDI, bit2=ZRN, bit3=MPG, bit4=JOG, bit5=INCJOG |
| **R8067** | ×10 (1000=100%) | Feed rate override | Записваем ✅ |
| **R8068** | ×10 (1000=100%) | Rapid override | Записваем ✅ |
| **R8069** | ×10 (1000=100%) | Spindle speed override | Записваем ✅ |
| **R20000** | bit register | CNC командни битове | bit1=Reset, bit10=CycleStart(MDI), bit11=StartMem⚠, bit12=Pause |
| **R21001** | M\_код × 1800 | M-code execution register | M10→18000, M11→19800, M3→5400, M5→9000 |
| **R22000** | int (1/4) | CNC режим | 1=MDI, 4=JOG — Записваем ✅ |
| **R5000–5008** | — | Modbus диагностика | connection, idle time, packet counters |

### Регистри с нулеви стойности на тази машина (неизползвани/грешно картографирани)
- R0–R13 (status word, X/Y/Z, feed, alarm, lot…) → **винаги 0**, контролерът не ги пълни
- R10000+ (абсолютни координати) → **винаги 0**
- R8102 (G-code line) → непотвърден, вероятно 0

---

## ✅ ПОТВЪРДЕНИ COILS (FC01 read-back, 0-base)

| Coil | Функция | Тип |
|---|---|---|
| 7 | Шпиндел работи (индикатор A) | Read-only, PLC Y-изход |
| 8 | Шпиндел работи (индикатор B) | Read-only, PLC Y-изход |
| 12 | Вакуум помпа ON/OFF | Read-only, PLC Y-изход |
| 14 + 18 | Forward Pos соленоид (A+B) | Read-only, PLC Y-изход |
| 15 + 19 | Left Pos соленоид (A+B) | Read-only, PLC Y-изход |
| 35 + 36 | Dust Cover (и двата ON = отворен) | Read-only, PLC Y-изход |

### ВАЖНО: Coils 0–255
FC05 write се **приема** (status=1) но PLC ги **презаписва в рамките на ~1ms**.  
Coils 512+ са sticky (тествано с coil 512) — но никакво известно machine mapping все още.

---

## ✅ ПОТВЪРДЕН MDI M-CODE EXECUTION PATH

```
1. Провери R22000 == 1 (MDI режим)
   Ако не → запиши R22000 = 1, изчакай 250ms

2. Запиши R21001 = M_код × 1800
   Примери: M10→18000, M11→19800, M3→5400, M5→9000, M17→30600

3. Пулс R20000 bit10 (Cycle Start):
   Запиши R20000 = 1024, изчакай 300ms, запиши R20000 = 0
```

### ⚠️ КРИТИЧЕН ПРОБЛЕМ: MDI буфер конфликт

**Cycle Start (bit10) изпълнява MDI TEXT БУФЕРА на контролера, НЕ директно R21001.**

- Когато потребителят е въвел M10 от HMI → буферът съдържа "M10"
- Записването на R21001=19800 (M11) + CycleStart → контролерът изпълнява M10 от буфера (игнорира R21001?)
- Потвърдено: M10 (vacuum ON) работи когато "M10" е в MDI буфера
- Потвърдено: M11 (vacuum OFF) НЕ работи надеждно ако буферът съдържа "M10"

**Хипотеза:** R21001 е READ регистър (контролерът записва текущия M-код там), не WRITE.  
Реалното управление може да изисква промяна в MDI text буфера директно — регистрите за MDI буфер не са намерени.

**Алтернатива:** R20000 bit11 (StartMem) изпълнява последния зареден NC файл — ОПАСНО.

### Регистри за изследване (MDI буфер)
- R22014–R22019: имаха ненулеви стойности когато MDI буферът съдържаше M10
- Кодировката не е намерена — нужен систематичен scan при различни MDI команди

---

## ✅ ПОТВЪРДЕНА M-CODE КАРТА (от BEIZA V3.pp + live capture)

| M-код | R21001 | Функция |
|---|---|---|
| M3 | 5400 | Шпиндел ON (CW) |
| M5 | 9000 | Шпиндел OFF |
| M10 | 18000 | Вакуум помпа 1 ON ✅ live |
| M11 | 19800 | Вакуум помпа 1 OFF (от PP footer) |
| M17 | 30600 | Почистващ цикъл (2 мин) |
| M30 | 54000 | Program End |
| **M140** | **?** | **Dust Cover UP** — 140×1800=252000 > 65535, различно кодиране |
| **M141** | **?** | **Dust Cover DOWN** — същото |

**Post-processor footer (BEIZA V3.pp):** `G28G91Z0` → `G49H0` → `M5M11` → `M17` → `M30`  
→ Вакумът **винаги се изключва** автоматично в края на всяка програма.

---

## ⚠️ НЕПОТВЪРДЕНИ / ЗА ИЗСЛЕДВАНЕ

### 1. M140/M141 — Dust Cover M-codes
- Формулата M×1800 надхвърля 16-bit за M140+ (252000 > 65535)
- **Как да намерим:** Следващия път когато машината изпълнява програма с dust cover → мониторирай R21001 по време на M140 изпълнение
- Debug script: `python debug_modbus.py` или `/api/scan` → watch R21001

### 2. MDI Text Buffer Registers
- R22014–R22019 показват ненулеви стойности при MDI, но кодировката е неизвестна
- **Как да намерим:** Scan R22000–R22050 при: (a) празен MDI буфер, (b) "M10" в буфера, (c) "M11" в буфера
- Ако намерим — можем да управляваме vacuum/spindle надеждно без HMI

### 3. Stopper M-codes
- Стоперите са PLC-контролирани, управлението от Modbus coil директно НЕ работи
- Вероятно има M-кодове в M100–M199 диапазон за стопери (специфични за машината)
- **Как да намерим:** Мониторирай R21001 когато машината изпълнява програма с автоматични стопери

### 4. SMB Share на контролера (за NC file loading)
- Контролерът е на 192.168.0.113, Windows CE база
- **Как да намерим:** `net view \\192.168.0.113` от CMD на PC-то → покажи shares
- Или: `Test-NetConnection 192.168.0.113 -Port 445` (SMB)
- Ако намерим → задай `NC_PROGRAMS_PATH=\\192.168.0.113\<share>\Program` в env

### 5. Tool Number Register
- R9000 е тест (неподвьрден) — може да е различен адрес
- **Как да намерим:** Смени инструмента от HMI → scan R8000–R9500 за промяна

### 6. Position Registers (X/Y/Z)
- R0–R13 са 0 — контролерът не ги пълни по подразбиране
- **Как да намерим:** В LNC параметри трябва да се конфигурира `Eth_ModbusServerTCP.ini` секция `[Register]`
- Или: R10000+ с правилен offset (в live scan при движение)

### 7. Feed Rate (активна скорост на програмата)
- R8 е 0, R1004 е моментална ос скорост
- Търси в R1000–R1010 диапазон при изпълнение на програма с F зададена

---

## 🔧 DEBUG СКРИПТОВЕ

### Бърз live monitor (PowerShell/Python)
```python
# Мониторинг на промени в регистри по време на операция
# Стартирай: python debug_modbus.py (вече съществува в репото)
```

### Scan по-широк диапазон (PowerShell)
```powershell
# От командния ред на Windows:
python -c "
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('192.168.0.113', port=502)
c.connect()
# Промени диапазона по нужда:
rr = c.read_holding_registers(address=22000, count=30, device_id=1)
for i,v in enumerate(rr.registers): 
    if v: print(f'R{22000+i} = {v}')
c.close()
"
```

### Live промени (watch)
```python
# Открива кои регистри се променят по време на операция
import time
from pymodbus.client import ModbusTcpClient
c = ModbusTcpClient('192.168.0.113', port=502)
c.connect()
START, COUNT = 21000, 20   # промени диапазона
prev = {}
while True:
    rr = c.read_holding_registers(address=START, count=COUNT, device_id=1)
    for i, v in enumerate(rr.registers):
        k = START + i
        if prev.get(k) != v:
            print(f'CHANGE R{k}: {prev.get(k, "?")} → {v}')
            prev[k] = v
    time.sleep(0.2)
```

---

## 📁 ФАЙЛОВА СТРУКТУРА

```
LNC-MW2200-BACKUP/
├── modbus_web/
│   ├── app.py              # Flask сървър — всички Modbus константи, API endpoints
│   ├── templates/index.html # Dashboard UI
│   ├── uploads/             # Качени NC файлове (auto-created)
│   ├── debug_modbus.py      # Debug скрипт
│   ├── scan_registers.py    # Scan скрипт
│   └── requirements.txt
├── disk4/machine/
│   ├── param.txt            # Параметри на машината
│   └── Eth_ModbusServerTCP.ini  # Modbus конфигурация (Port=502, RegisterMode=-32)
├── disk3/data/
│   ├── open_custom_bottom/ohframe.xml  # HMI панел бутони
│   └── open_mill_ext/ohframe.xml       # Mill extension HMI (R20000 bit map потвърден тук)
├── BEIZA V3.pp              # Post-processor — SOURCE OF TRUTH за M-кодове
└── MODBUS_DISCOVERY.md      # Този файл
```

---

## 🚀 СТАРТИРАНЕ НА DASHBOARD

```bash
# Провери за зомби процеси
netstat -ano | findstr :5000

# Убий ако има
Stop-Process -Id <PID> -Force

# Стартирай
cd "D:\LNC BACKUP\LNC-MW2200-BACKUP\modbus_web"
python app.py
# → http://localhost:5000
```

### Environment variables
```
MODBUS_HOST=192.168.0.113    # IP на контролера (default)
MODBUS_PORT=502               # Modbus TCP порт (default)
NC_PROGRAMS_PATH=             # SMB path към папката с програми (ако намерим)
```

---

## ⚡ API ENDPOINTS

| Метод | URL | Описание |
|---|---|---|
| GET | `/api/status` | Пълен machine state JSON |
| POST | `/api/mcode` | `{"mcode":"vacuum_on"}` — MDI M-code изпълнение |
| POST | `/api/command` | `{"command":"cycle_start","value":true}` — coil write |
| POST | `/api/load_program` | multipart file upload (.nc/.gcode/.tap) |
| GET | `/api/uploads` | Списък качени файлове |
| GET | `/api/scan` | Live register scan |
| GET | `/api/diagnostics` | Пълна диагностика |
| POST | `/api/override` | `{"type":"feed","value":100}` — override % |

---

## 🎯 ПРИОРИТЕТИ ЗА СЛЕДВАЩАТА СЕСИЯ

1. **Fix vacuum OFF** — намери MDI буфер регистрите (R22014–R22019 scan)  
2. **M140/M141 encoding** — мониторирай R21001 при dust cover операция  
3. **SMB share** — `net view \\192.168.0.113` → конфигурирай NC_PROGRAMS_PATH  
4. **Tool number** — смени инструмент → scan R8000–R9500  
5. **Stopper M-codes** — мониторирай R21001 при автоматична програма с стопери  
6. **Feed rate register** — R1000–R1010 при активна програма с F команда
