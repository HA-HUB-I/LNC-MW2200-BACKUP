let currentUnit = 'mm';
let lastData = null;

function toggleUnits() {
    currentUnit = currentUnit === 'mm' ? 'cm' : 'mm';
    document.getElementById('unit-btn').textContent = currentUnit.toUpperCase();
    updateUI();
}

function formatPos(val) {
    if (!val && val !== 0) return "0.000";
    return currentUnit === 'cm' ? (val / 10).toFixed(4) : val.toFixed(3);
}

function updateUI() {
    if (!lastData) return;
    const d = lastData;

    // Coords
    document.getElementById('val-x').textContent = formatPos(d.x_pos);
    document.getElementById('val-y').textContent = formatPos(d.y_pos);
    document.getElementById('val-z').textContent = formatPos(d.z_pos);
    document.getElementById('val-abs-x').textContent = "Abs: " + formatPos(d.abs_x_pos);
    document.getElementById('val-abs-y').textContent = "Abs: " + formatPos(d.abs_y_pos);
    document.getElementById('val-abs-z').textContent = "Abs: " + formatPos(d.abs_z_pos);

    // Speeds & RPM
    document.getElementById('val-spindle').textContent = d.spindle_rpm;
    document.getElementById('bar-spindle').style.width = Math.min(100, (d.spindle_rpm / 24000) * 100) + "%";
    document.getElementById('val-feed').textContent = d.feed_rate;
    document.getElementById('bar-feed').style.width = Math.min(100, (d.feed_rate / 15000) * 100) + "%";
    document.getElementById('fl-ovr-f').textContent = `FEED: ${d.feed_override_pct}%`;
    document.getElementById('fl-ovr-s').textContent = `SPDL: ${d.spindle_override_pct}%`;

    // Flags
    const setFl = (id, act, cls='active') => {
        const el = document.getElementById(id);
        if(el) act ? el.classList.add(cls) : el.classList.remove(cls);
    };
    setFl('fl-cycle', d.cycle_running);
    setFl('fl-spindle', d.spindle_on || d.spindle_running);
    setFl('fl-alarm', d.alarm_active, 'active-red');
    setFl('fl-estop', d.estop_active, 'active-red');
    setFl('fl-vacuum', d.vacuum_on);
    setFl('fl-fwd', d.forward_pos_on);
    setFl('fl-left', d.left_pos_on);
    setFl('fl-right', d.right_pos_on);

    // Modes
    const MODES = ['MEM','MDI','JOG','INCJOG','MPG','ZRN'];
    MODES.forEach(m => {
        const el = document.getElementById('m-'+m);
        if(el) el.className = 'mode-tag' + (d.cnc_mode===m?' active':'');
    });

    // --- WARNING BAR LOGIC ---
    const wb = document.getElementById('warning-bar');
    let warnings = [];
    if (d.spindle_on || d.spindle_running) {
        warnings.push('<div class="warning-item orange">⚠️ ШПИНДЕЛЪТ РАБОТИ!</div>');
    }
    if (d.forward_pos_on || d.left_pos_on || d.right_pos_on) {
        warnings.push('<div class="warning-item red">⚠️ СТОПЕРИТЕ СА АКТИВНИ!</div>');
    }
    if (d.alarm_active) {
        warnings.push(`<div class="warning-item red">🚨 АЛАРМА: ${d.alarm_code || ''}</div>`);
    }

    if (warnings.length > 0) {
        wb.style.display = 'flex';
        wb.innerHTML = warnings.join('');
    } else {
        wb.style.display = 'none';
    }
}

async function fetchStatus() {
    try {
        const r = await fetch('/api/status');
        lastData = await r.json();
        updateUI();
        document.getElementById('conn-status').style.color = 'var(--green)';
    } catch(e) {
        document.getElementById('conn-status').style.color = 'var(--red)';
    }
}

async function fetchDiagLog() {
    try {
        const r = await fetch('/api/diag_history');
        const d = await r.json();
        const tbody = document.querySelector('#diag-log-table tbody');
        if (tbody) {
            tbody.innerHTML = d.logs.map(l => `<tr><td>${l.time}</td><td style="color:var(--accent)">R${l.addr}</td><td>${l.val}</td><td style="color:var(--orange)">${l.delta}</td></tr>`).join('');
        }
    } catch(e) {}
}

async function runScan() {
    try {
        const r = await fetch('/api/scan');
        const d = await r.json();
        const tbody = document.querySelector('#scan-table tbody');
        if (tbody) {
            tbody.innerHTML = d.scans.map(s => `<tr><td>R${s.address}</td><td><small>${s.description}</small></td><td class="val">${s.raw_value}</td></tr>`).join('');
        }
    } catch(e) {}
}

setInterval(fetchStatus, 500);
setInterval(fetchDiagLog, 1000);
fetchStatus();
