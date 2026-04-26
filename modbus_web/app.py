import threading
from dataclasses import asdict
from flask import Flask, jsonify, render_template, request, send_from_directory
from core.models import MachineState
from core.modbus_worker import ModbusWorker
from core.config import *
from core.utils import list_uploaded_files, save_nc_file

app = Flask(__name__)

# Global state and worker
state = MachineState()
lock = threading.Lock()
worker = ModbusWorker(state, lock)
worker.start()

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
        scans.append({"address": 11565, "description": "Work Y", "raw_value": int(state.y_pos * 1000)})
        scans.append({"address": 11570, "description": "Work X", "raw_value": int(state.x_pos * 1000)})
        scans.append({"address": 11633, "description": "Work Z", "raw_value": int(state.z_pos * 1000)})
    return jsonify(scans=scans)

@app.route('/manifest.json')
def serve_manifest(): return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def serve_sw(): return send_from_directory('static', 'sw.js')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
