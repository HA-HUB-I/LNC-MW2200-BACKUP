import threading
from dataclasses import asdict
from flask import Flask, jsonify, render_template, request, send_from_directory
from core.models import MachineState
from core.modbus_worker import ModbusWorker
from core.config import *

app = Flask(__name__)

# Глобално състояние
state = MachineState()
lock = threading.Lock()

# Стартиране на Modbus работника
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
    
    mapping = {
        "cycle_start": C_START,
        "feed_hold": C_HOLD,
        "reset": C_RESET,
        "estop": C_ESTOP,
        "vacuum_on": C_VACUUM,
    }
    
    if cmd in mapping:
        worker.send_coil(mapping[cmd], True)
        return jsonify(ok=True)
    return jsonify(ok=False, error="Unknown command"), 400

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
