/**
 * app.js — Hexapod control dashboard
 *
 * Responsibilities:
 *  - WebSocket client with exponential-backoff reconnect
 *  - Canvas-based top-down hex leg visualisation
 *  - Gait mode buttons (POST /gait/{mode})
 *  - Body pose sliders (POST /pose)
 *  - Velocity joystick — drag = vx/vy, Shift+drag = omega
 *  - Keyboard control: WASD + QE
 *  - IMU gauge updates
 *  - Sensor distance bars
 */

'use strict';

// ── Configuration ─────────────────────────────────────────────────────────────
const API_BASE  = `${location.protocol}//${location.host}`;
const WS_URL    = `ws://${location.host}/ws/telemetry`;
const MAX_DIST  = 200;   // cm — full sensor bar scale
const STEP_VX   = 0.06;  // m/s per keypress
const STEP_OMEGA = 30.0; // deg/s per keypress

// ── DOM refs ──────────────────────────────────────────────────────────────────
const overlay       = document.getElementById('overlay');
const overlayMsg    = document.getElementById('overlay-msg');
const connStatus    = document.getElementById('conn-status');
const gaitBadge     = document.getElementById('gait-badge');
const angleTbody    = document.getElementById('angle-tbody');
const canvas        = document.getElementById('hex-canvas');
const ctx           = canvas.getContext('2d');
const joystickZone  = document.getElementById('joystick-zone');
const joystickThumb = document.getElementById('joystick-thumb');

// Sliders
const heightSlider = document.getElementById('height-slider');
const pitchSlider  = document.getElementById('pitch-slider');
const rollSlider   = document.getElementById('roll-slider');
const heightVal    = document.getElementById('height-val');
const pitchVal     = document.getElementById('pitch-val');
const rollLabel    = document.getElementById('roll-slider-label');

// ── State ─────────────────────────────────────────────────────────────────────
let ws               = null;
let reconnectDelay   = 1000;
let currentMode      = 'stand';
let vx = 0, vy = 0, omega = 0;
let joystickActive   = false;
let joystickShift    = false;
let joystickOrigin   = { x: 0, y: 0 };
const keysHeld       = new Set();

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connectWS() {
  overlayMsg.textContent = `Connecting (retry in ${(reconnectDelay / 1000).toFixed(1)} s)…`;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    reconnectDelay = 1000;
    overlay.classList.add('hidden');
    connStatus.textContent = 'CONNECTED';
    connStatus.className = 'badge badge-connected';
    console.log('WebSocket connected');
  };

  ws.onmessage = (evt) => {
    let data;
    try { data = JSON.parse(evt.data); } catch { return; }
    updateUI(data);
  };

  ws.onclose = () => {
    connStatus.textContent = 'DISCONNECTED';
    connStatus.className = 'badge badge-disconnected';
    overlay.classList.remove('hidden');
    overlayMsg.textContent = `Reconnecting in ${(reconnectDelay / 1000).toFixed(1)} s…`;
    setTimeout(connectWS, reconnectDelay);
    reconnectDelay = Math.min(reconnectDelay * 2, 30_000);
  };

  ws.onerror = () => ws.close();
}

// ── UI update from telemetry ──────────────────────────────────────────────────
function updateUI(data) {
  if (data.gait_mode) {
    currentMode = data.gait_mode;
    gaitBadge.textContent = data.gait_mode.toUpperCase();
    document.querySelectorAll('.gait-btn').forEach(b => {
      b.classList.toggle('active', b.dataset.mode === data.gait_mode);
    });
  }

  if (data.angles) {
    updateAngles(data.angles);
    drawHexCanvas(data.angles);
  }

  if (data.imu) {
    const imu = data.imu;
    // Compute roll/pitch from accel (simplified display)
    const rollDeg  = Math.atan2(imu.ay, imu.az) * 180 / Math.PI;
    const pitchDeg = Math.atan2(-imu.ax, Math.hypot(imu.ay, imu.az)) * 180 / Math.PI;
    document.getElementById('imu-roll').textContent  = rollDeg.toFixed(1) + '°';
    document.getElementById('imu-pitch').textContent = pitchDeg.toFixed(1) + '°';
    document.getElementById('imu-temp').textContent  = imu.temp_c.toFixed(1) + '°C';
    // Bars: map ±45° → 0–100 %
    document.getElementById('bar-roll').style.width  = clamp(50 + rollDeg * 50 / 45, 0, 100) + '%';
    document.getElementById('bar-pitch').style.width = clamp(50 + pitchDeg * 50 / 45, 0, 100) + '%';
  }

  if (data.sensors) {
    const ids   = ['left', 'center', 'right'];
    const barIds = ['bar-left', 'bar-center', 'bar-right'];
    const distIds = ['dist-left', 'dist-center', 'dist-right'];
    data.sensors.forEach((d, i) => {
      const pct = clamp(d / MAX_DIST * 100, 0, 100);
      const bar = document.getElementById(barIds[i]);
      bar.style.width = pct + '%';
      bar.className = 'sensor-bar' + (d < 20 ? ' danger' : d < 50 ? ' warning' : '');
      document.getElementById(distIds[i]).textContent = d < 0 ? '--' : d.toFixed(0) + ' cm';
    });
  }
}

function updateAngles(angles) {
  // Build or update table rows
  if (angleTbody.children.length !== 6) {
    angleTbody.innerHTML = '';
    for (let i = 0; i < 6; i++) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>Leg ${i}</td><td>—</td><td>—</td><td>—</td>`;
      angleTbody.appendChild(tr);
    }
  }
  angles.forEach(([c, f, t], i) => {
    const cells = angleTbody.children[i].cells;
    cells[1].textContent = c.toFixed(1) + '°';
    cells[2].textContent = f.toFixed(1) + '°';
    cells[3].textContent = t.toFixed(1) + '°';
  });
}

// ── Canvas visualisation ──────────────────────────────────────────────────────
const LEG_ANGLES_DEG = [45, -45, 90, -90, 135, -135];
const BODY_RADIUS_PX = 60;
const LEG_LENGTH_PX  = 90;
const COLORS = ['#58a6ff', '#3fb950', '#d29922', '#f85149', '#a371f7', '#39d353'];

function drawHexCanvas(angles) {
  const W = canvas.width, H = canvas.height;
  const cx = W / 2, cy = H / 2;
  ctx.clearRect(0, 0, W, H);

  // Body hexagon
  ctx.beginPath();
  for (let i = 0; i < 6; i++) {
    const a = Math.PI / 3 * i - Math.PI / 6;
    const px = cx + BODY_RADIUS_PX * Math.cos(a);
    const py = cy + BODY_RADIUS_PX * Math.sin(a);
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.fillStyle = '#21262d';
  ctx.strokeStyle = '#30363d';
  ctx.lineWidth = 2;
  ctx.fill();
  ctx.stroke();

  // Forward indicator
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx, cy - BODY_RADIUS_PX - 10);
  ctx.strokeStyle = '#58a6ff';
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = '#58a6ff';
  ctx.font = '11px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText('FWD', cx, cy - BODY_RADIUS_PX - 14);

  // Each leg
  angles.forEach(([coxa, femur, tibia], i) => {
    const baseAngle = LEG_ANGLES_DEG[i] * Math.PI / 180;
    // Coxa attachment point on body
    const ax = cx + BODY_RADIUS_PX * Math.cos(baseAngle);
    const ay = cy - BODY_RADIUS_PX * Math.sin(baseAngle);

    // Use coxa angle to offset direction slightly
    const legAngle = baseAngle - (coxa * Math.PI / 180) * 0.3;
    const reach = LEG_LENGTH_PX * (0.5 + tibia / 360);

    const fx = ax + reach * Math.cos(legAngle);
    const fy = ay - reach * Math.sin(legAngle);

    ctx.beginPath();
    ctx.moveTo(ax, ay);
    ctx.lineTo(fx, fy);
    ctx.strokeStyle = COLORS[i];
    ctx.lineWidth = 3;
    ctx.stroke();

    // Foot dot
    ctx.beginPath();
    ctx.arc(fx, fy, 6, 0, Math.PI * 2);
    ctx.fillStyle = COLORS[i];
    ctx.fill();

    // Leg label
    ctx.fillStyle = '#8b949e';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(i, (ax + fx) / 2, (ay + fy) / 2 - 4);
  });
}

// ── Gait buttons ──────────────────────────────────────────────────────────────
document.querySelectorAll('.gait-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const mode = btn.dataset.mode;
    postGait(mode);
  });
});

async function postGait(mode) {
  try {
    const res = await fetch(`${API_BASE}/gait/${mode}`, { method: 'POST' });
    if (res.ok) {
      currentMode = mode;
      gaitBadge.textContent = mode.toUpperCase();
      document.querySelectorAll('.gait-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === mode);
      });
    }
  } catch (e) {
    console.warn('Gait request failed:', e);
  }
}

// ── Pose sliders ──────────────────────────────────────────────────────────────
function sendPose() {
  const height = parseFloat(heightSlider.value) / 100;
  const pitch  = parseFloat(pitchSlider.value);
  const roll   = parseFloat(rollSlider.value);
  heightVal.textContent = heightSlider.value + ' cm';
  pitchVal.textContent  = pitch + '°';
  rollLabel.textContent = roll + '°';
  fetch(`${API_BASE}/pose`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ height, pitch, roll, yaw_rate: 0 }),
  }).catch(() => {});
}

[heightSlider, pitchSlider, rollSlider].forEach(s => s.addEventListener('input', sendPose));

// ── Velocity ──────────────────────────────────────────────────────────────────
function sendVelocity(nvx, nvy, nomega) {
  vx = nvx; vy = nvy; omega = nomega;
  fetch(`${API_BASE}/velocity`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vx, vy, omega }),
  }).catch(() => {});
}

// ── Joystick ──────────────────────────────────────────────────────────────────
const JOY_RADIUS = 55;  // px — max thumb displacement

function joystickStart(x, y, shift) {
  joystickActive = true;
  joystickShift  = shift;
  const rect = joystickZone.getBoundingClientRect();
  joystickOrigin = {
    x: rect.left + rect.width / 2,
    y: rect.top  + rect.height / 2,
  };
  joystickMove(x, y);
}

function joystickMove(x, y) {
  if (!joystickActive) return;
  let dx = x - joystickOrigin.x;
  let dy = y - joystickOrigin.y;
  const dist = Math.hypot(dx, dy);
  if (dist > JOY_RADIUS) {
    dx = dx / dist * JOY_RADIUS;
    dy = dy / dist * JOY_RADIUS;
  }
  joystickThumb.style.left = (75 + dx) + 'px';
  joystickThumb.style.top  = (75 + dy) + 'px';

  const nx = dx / JOY_RADIUS;   // -1 .. 1
  const ny = dy / JOY_RADIUS;   // -1 .. 1

  if (joystickShift) {
    sendVelocity(0, 0, -nx * 90);
  } else {
    sendVelocity(-ny * 0.15, -nx * 0.15, 0);
  }
}

function joystickEnd() {
  joystickActive = false;
  joystickThumb.style.left = '50%';
  joystickThumb.style.top  = '50%';
  sendVelocity(0, 0, 0);
}

joystickZone.addEventListener('mousedown',  e => joystickStart(e.clientX, e.clientY, e.shiftKey));
joystickZone.addEventListener('touchstart', e => {
  const t = e.touches[0];
  joystickStart(t.clientX, t.clientY, false);
  e.preventDefault();
}, { passive: false });

window.addEventListener('mousemove',  e => joystickMove(e.clientX, e.clientY));
window.addEventListener('touchmove',  e => {
  const t = e.touches[0];
  joystickMove(t.clientX, t.clientY);
  e.preventDefault();
}, { passive: false });

window.addEventListener('mouseup',   joystickEnd);
window.addEventListener('touchend',  joystickEnd);

// ── Keyboard ──────────────────────────────────────────────────────────────────
const KEY_VX = { KeyW: STEP_VX, KeyS: -STEP_VX };
const KEY_VY = { KeyA: STEP_VX, KeyD: -STEP_VX };
const KEY_OM = { KeyQ: STEP_OMEGA, KeyE: -STEP_OMEGA };

function applyKeys() {
  let nvx = 0, nvy = 0, nom = 0;
  keysHeld.forEach(k => {
    if (KEY_VX[k]) nvx += KEY_VX[k];
    if (KEY_VY[k]) nvy += KEY_VY[k];
    if (KEY_OM[k]) nom += KEY_OM[k];
  });
  sendVelocity(nvx, nvy, nom);
}

document.addEventListener('keydown', e => {
  if (e.code === 'Space') { e.preventDefault(); sendVelocity(0, 0, 0); return; }
  if (!keysHeld.has(e.code)) {
    keysHeld.add(e.code);
    applyKeys();
  }
});

document.addEventListener('keyup', e => {
  keysHeld.delete(e.code);
  applyKeys();
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

// ── Boot ──────────────────────────────────────────────────────────────────────
connectWS();
// Draw empty canvas on load
drawHexCanvas([[90,90,90],[90,90,90],[90,90,90],[90,90,90],[90,90,90],[90,90,90]]);
