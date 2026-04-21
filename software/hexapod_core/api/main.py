"""
Hexapod REST + WebSocket API.

Endpoints
---------
GET  /                    — health check
GET  /status              — current state JSON
POST /gait/{mode}         — change gait mode (tripod|wave|ripple|stand|stop)
POST /pose                — set body pose {pitch, roll, yaw, height}
POST /velocity            — set velocity {vx, vy, omega}
POST /servo/{ch}/angle    — manual servo override (angle in request body)
GET  /ws/telemetry        — WebSocket stream (10 Hz): angles, IMU, sensors
GET  /stream/video        — MJPEG video stream placeholder (if camera enabled)

Environment variables
---------------------
I2C_BUS           : int   — I²C bus number (default 1)
PCA9685_ADDRESS   : int   — PCA9685 I²C address in hex (default 0x40)
LOG_LEVEL         : str   — Python logging level (default INFO)
CAMERA_ENABLED    : bool  — enable MJPEG stream (default false)
TICK_RATE_HZ      : float — control loop rate (default 50)
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from hexapod_core.gait import GaitEngine, GaitMode, StepParams
from hexapod_core.hardware import ImuData, MPU6050, PCA9685, SensorArray
from hexapod_core.kinematics import LegIK

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("hexapod.api")

# ── Configuration ─────────────────────────────────────────────────────────────
_I2C_BUS = int(os.getenv("I2C_BUS", "1"))
_PCA9685_ADDR = int(os.getenv("PCA9685_ADDRESS", "0x40"), 16)
_CAMERA_ENABLED = os.getenv("CAMERA_ENABLED", "false").lower() == "true"
_TICK_RATE_HZ = float(os.getenv("TICK_RATE_HZ", "50"))

# ── Pydantic models ───────────────────────────────────────────────────────────


class PoseRequest(BaseModel):
    pitch: float = Field(0.0, ge=-30.0, le=30.0, description="Pitch in degrees")
    roll: float = Field(0.0, ge=-30.0, le=30.0, description="Roll in degrees")
    yaw_rate: float = Field(0.0, ge=-90.0, le=90.0, description="Yaw rate deg/s")
    height: float = Field(-0.10, ge=-0.18, le=-0.04, description="Body height (m, negative)")


class VelocityRequest(BaseModel):
    vx: float = Field(0.0, ge=-0.3, le=0.3, description="Forward velocity m/s")
    vy: float = Field(0.0, ge=-0.3, le=0.3, description="Lateral velocity m/s")
    omega: float = Field(0.0, ge=-90.0, le=90.0, description="Yaw rate deg/s")


class GaitResponse(BaseModel):
    mode: str
    ok: bool = True


class AngleRequest(BaseModel):
    angle: float = Field(..., ge=0.0, le=180.0, description="Servo angle 0–180°")


# ── Global application state ──────────────────────────────────────────────────

class AppState:
    """Mutable application state shared across request handlers."""

    def __init__(self) -> None:
        self.ik = LegIK()
        self.params = StepParams()
        self.gait_engine = GaitEngine(self.ik, self.params)
        self.pca: Optional[PCA9685] = None
        self.imu: Optional[MPU6050] = None
        self.sensors: Optional[SensorArray] = None
        self.current_angles: List[tuple] = [(90.0, 90.0, 90.0)] * 6
        self.imu_data: ImuData = ImuData()
        self.sensor_distances: List[float] = [100.0, 100.0, 100.0]
        self._tick_task: Optional[asyncio.Task] = None
        self._ws_clients: List[WebSocket] = []


_state = AppState()


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise hardware on startup; clean up on shutdown."""
    logger.info("Initialising hardware (bus=%d, PCA9685 addr=0x%02X)…", _I2C_BUS, _PCA9685_ADDR)

    _state.pca = PCA9685(bus=_I2C_BUS, address=_PCA9685_ADDR)
    _state.imu = MPU6050(bus=_I2C_BUS)
    _state.sensors = SensorArray.create_hcsr04_triplet()

    # Start control loop
    _state._tick_task = asyncio.create_task(_control_loop())
    logger.info("Hexapod API ready — control loop running at %.0f Hz.", _TICK_RATE_HZ)

    yield  # ← application runs here

    # Shutdown
    logger.info("Shutting down hexapod API…")
    if _state._tick_task:
        _state._tick_task.cancel()
        try:
            await _state._tick_task
        except asyncio.CancelledError:
            pass
    if _state.pca:
        _state.pca.reset()
        _state.pca.close()
    if _state.imu:
        _state.imu.close()
    if _state.sensors:
        _state.sensors.cleanup()
    logger.info("Shutdown complete.")


# ── FastAPI app ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Hexapod API",
    version="0.1.0",
    description="REST + WebSocket control API for the STEM hexapod robot.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Control loop ──────────────────────────────────────────────────────────────

async def _control_loop() -> None:
    """Background task: run gait engine at TICK_RATE_HZ and drive servos."""
    dt = 1.0 / _TICK_RATE_HZ
    ws_interval = 0.1   # broadcast telemetry every 100 ms
    ws_counter = 0.0

    while True:
        t0 = time.monotonic()

        # Advance gait engine
        angles = _state.gait_engine.tick(dt)
        _state.current_angles = angles

        # Drive servos
        if _state.pca:
            flat = []
            for coxa, femur, tibia in angles:
                flat.extend([coxa, femur, tibia])
            _state.pca.set_all_servos(flat)

        # Read sensors at slower rate
        ws_counter += dt
        if ws_counter >= ws_interval:
            ws_counter = 0.0
            if _state.imu:
                _state.imu_data = _state.imu.read()
            if _state.sensors:
                _state.sensor_distances = _state.sensors.scan()
            # Broadcast telemetry
            await _broadcast_telemetry()

        # Sleep remainder of tick
        elapsed = time.monotonic() - t0
        sleep_time = max(0.0, dt - elapsed)
        await asyncio.sleep(sleep_time)


async def _broadcast_telemetry() -> None:
    """Send a telemetry JSON frame to all connected WebSocket clients."""
    if not _state._ws_clients:
        return

    imu = _state.imu_data
    payload = {
        "timestamp": time.time(),
        "angles": [list(a) for a in _state.current_angles],
        "imu": {
            "ax": round(imu.ax, 3),
            "ay": round(imu.ay, 3),
            "az": round(imu.az, 3),
            "gx": round(imu.gx, 2),
            "gy": round(imu.gy, 2),
            "gz": round(imu.gz, 2),
            "temp_c": round(imu.temp_c, 1),
        },
        "sensors": _state.sensor_distances,
        "gait_mode": _state.gait_engine._mode.value,
    }
    msg = json.dumps(payload)
    disconnected: List[WebSocket] = []
    for ws in _state._ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        _state._ws_clients.remove(ws)


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/", tags=["health"])
async def root() -> Dict[str, Any]:
    """Health check."""
    return {"status": "ok", "service": "hexapod-core", "version": "0.1.0"}


@app.get("/status", tags=["status"])
async def status() -> Dict[str, Any]:
    """Return current robot state."""
    imu = _state.imu_data
    return {
        "gait_mode": _state.gait_engine._mode.value,
        "angles": [list(a) for a in _state.current_angles],
        "imu": {
            "ax": imu.ax, "ay": imu.ay, "az": imu.az,
            "gx": imu.gx, "gy": imu.gy, "gz": imu.gz,
            "temp_c": imu.temp_c,
        },
        "sensors": _state.sensor_distances,
    }


_GAIT_MAP = {
    "tripod": GaitMode.TRIPOD,
    "wave": GaitMode.WAVE,
    "ripple": GaitMode.RIPPLE,
    "stand": GaitMode.STAND,
    "stop": GaitMode.STAND,
}


@app.post("/gait/{mode}", response_model=GaitResponse, tags=["control"])
async def set_gait(mode: str) -> GaitResponse:
    """Change gait mode."""
    mode_lower = mode.lower()
    if mode_lower not in _GAIT_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown gait mode '{mode}'. Valid: {list(_GAIT_MAP.keys())}",
        )
    _state.gait_engine.set_mode(_GAIT_MAP[mode_lower])
    logger.info("Gait mode → %s", mode_lower)
    return GaitResponse(mode=mode_lower)


@app.post("/pose", tags=["control"])
async def set_pose(req: PoseRequest) -> Dict[str, Any]:
    """Set body pose (pitch, roll, yaw_rate, height)."""
    p = _state.params
    p.pitch = req.pitch
    p.roll = req.roll
    p.yaw_rate = req.yaw_rate
    p.body_height = req.height
    _state.gait_engine.set_params(p)
    return {"ok": True, "pose": req.model_dump()}


@app.post("/velocity", tags=["control"])
async def set_velocity(req: VelocityRequest) -> Dict[str, Any]:
    """Set translational and rotational velocity."""
    _state.gait_engine.set_velocity(req.vx, req.vy, req.omega)
    logger.debug("Velocity: vx=%.3f vy=%.3f omega=%.1f", req.vx, req.vy, req.omega)
    return {"ok": True, "velocity": req.model_dump()}


@app.post("/servo/{ch}/angle", tags=["control"])
async def set_servo_angle(ch: int, req: AngleRequest) -> Dict[str, Any]:
    """Manually override a servo channel (0–17)."""
    if not 0 <= ch <= 17:
        raise HTTPException(status_code=422, detail="Channel must be 0–17.")
    if _state.pca:
        _state.pca.set_servo_angle(ch, req.angle)
    return {"ok": True, "channel": ch, "angle": req.angle}


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def ws_telemetry(websocket: WebSocket) -> None:
    """WebSocket endpoint that streams telemetry at 10 Hz."""
    await websocket.accept()
    _state._ws_clients.append(websocket)
    logger.info("WebSocket client connected (total: %d).", len(_state._ws_clients))
    try:
        while True:
            # Keep connection alive; send pings so client knows we're active
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _state._ws_clients:
            _state._ws_clients.remove(websocket)
        logger.info("WebSocket client disconnected (total: %d).", len(_state._ws_clients))


@app.get("/stream/video", tags=["vision"])
async def stream_video():
    """MJPEG video stream (requires hexapod-vision service and CAMERA_ENABLED=true)."""
    if not _CAMERA_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Camera not enabled. Set CAMERA_ENABLED=true and start the vision service.",
        )
    # In the monolithic deployment, proxy to vision service is handled by nginx.
    raise HTTPException(status_code=503, detail="Route to vision service via nginx proxy.")
