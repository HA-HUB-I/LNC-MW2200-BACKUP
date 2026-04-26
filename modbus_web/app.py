import threading
import logging
from dataclasses import asdict
from flask import Flask, jsonify, render_template, request, send_from_directory
from core.models import MachineState
from core.modbus_worker import ModbusWorker
from core.diagnostic_worker import DiagnosticWorker
from core.config import *
from core.utils import list_uploaded_files, save_nc_file

app = Flask(__name__)

# Global state and workers
state = MachineState()
lock = threading.Lock()
worker = ModbusWorker(state, lock)
worker.start()

# Start Diagnostic Logger
diag_worker = DiagnosticWorker(DIAGNOSTIC_WATCH_LIST)
diag_worker.start()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    with lock:
        return jsonify(asdict(state))

@app.route("/api/command", methods=["POST"])
def api_command():
    body = request.get_json(force=True, silent=True) or {}
    cmd = body.get("command")
    mapping = {"cycle_start": 0, "feed_hold": 1, "reset": 2, "estop": 6}
    if cmd in mapping:
        worker.write_coil(mapping[cmd], True)
        return jsonify(ok=True)
    return jsonify(ok=False), 400

@app.route("/api/mcode", methods=["POST"])
def api_mcode():
    body = request.get_json(force=True, silent=True) or {}
    mcode = body.get("mcode")
    # M10/M11 for Vacuum
    if mcode == "vacuum_on": worker.write_register(21001, 10 * 1800)
    elif mcode == "vacuum_off": worker.write_register(21001, 11 * 1800)
    return jsonify(ok=True)

@app.route("/api/uploads")
def api_uploads():
    return jsonify(files=list_uploaded_files())

@app.route("/api/load_program", methods=["POST"])
def api_load_program():
    if "file" not in request.files: return jsonify(ok=False), 400
    ok, msg = save_nc_file(request.files["file"])
    return jsonify(ok=ok, message=msg)

@app.route("/api/scan")
def api_scan():
    # Quick scan for UI feedback
    scans = []
    with lock:
        scans.append({"address": 11565, "description": "Machine Y", "raw_value": int(state.y_pos * 1000)})
        scans.append({"address": 11570, "description": "Machine X", "raw_value": int(state.x_pos * 1000)})
        scans.append({"address": 11560, "description": "Machine Z", "raw_value": int(state.z_pos * 1000)})
        scans.append({"address": 12034, "description": "Absolute Z", "raw_value": int(state.abs_z_pos * 1000)})
    return jsonify(scans=scans)

@app.route("/api/diag_history")
def api_diag_history():
    log_file = "modbus_web/logs/diagnostic_history.csv"
    if not os.path.exists(log_file):
        return jsonify(logs=[])
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Връщаме последните 20 промени
            last_lines = lines[-20:] if len(lines) > 20 else lines[1:]
            logs = []
            for line in reversed(last_lines):
                parts = line.strip().split(',')
                if len(parts) >= 5:
                    logs.append({
                        "time": parts[0].split(' ')[1], # Само часа
                        "addr": parts[1],
                        "val": parts[3],
                        "delta": parts[4]
                    })
            return jsonify(logs=logs)
    except:
        return jsonify(logs=[])

@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')

if __name__ == "__main__":
    # Спираме досадните логове на Flask за 200 OK
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    print("--- LNC DASHBOARD SERVER STARTED ---")
    print("URL: http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
