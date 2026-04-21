# Software Architecture

## System Overview

```
┌───────────────────────────────────────────────────────────────────────┐
│                          Browser / Client                             │
│              index.html · app.js · style.css  (port 80)              │
└───────────────────────────────┬───────────────────────────────────────┘
                                │ HTTP REST + WebSocket
                    ┌───────────▼───────────┐
                    │      nginx (UI)        │
                    │   Reverse Proxy :80   │
                    └───────┬───────┬───────┘
                   /api/    │       │ /ws/
           ┌───────▼──────┐ │ ┌─────▼──────────────────┐
           │  FastAPI Core │ │ │  WebSocket Telemetry   │
           │  REST  :8000  │ │ │  10 Hz broadcast       │
           └───────┬───────┘ │ └─────┬──────────────────┘
                   │         │       │
        ┌──────────┼─────────┘       │
        │          │                 │
┌───────▼──┐ ┌─────▼──────┐ ┌───────▼───────┐
│ Gait     │ │ IK Solver  │ │ Hardware      │
│ Engine   │ │ (analytic) │ │ Drivers       │
│ 50 Hz    │ │            │ │ PCA9685       │
│ tick     │ │ 3-DOF /leg │ │ MPU-6050      │
└───────┬──┘ └────────────┘ │ HC-SR04 × 3   │
        │                   └───────────────┘
        │ I²C / GPIO
┌───────▼──────────────────────────────────┐
│              Raspberry Pi 4              │
│   /dev/i2c-1   /dev/gpiomem             │
└──────────────────────────────────────────┘
```

---

## Service Descriptions

### hexapod-core (port 8000)

The main control service.  Runs on the Raspberry Pi inside Docker.

- **GaitEngine** advances leg positions at 50 Hz.
- **LegIK** converts foot XYZ → servo angles.
- **PCA9685** driver writes PWM values to all 18 servos.
- **MPU6050** driver reads IMU orientation at 10 Hz.
- **SensorArray** reads all 3 HC-SR04 sensors at 10 Hz.
- **FastAPI** exposes REST endpoints and a WebSocket telemetry stream.

### hexapod-ui (port 80)

A minimal nginx container serving:
- Static files: `index.html`, `app.js`, `style.css`.
- Reverse proxy: `/api/` → hexapod-core:8000, `/ws/` → WebSocket.

### hexapod-vision (port 8001, optional)

Camera service using OpenCV.  MJPEG stream available at `/stream/video`.

---

## IK Solver — Mathematical Derivation

### Coordinate system

```
         Z (up)
         │
         │
         └─── X (forward)
        /
       Y (left)
```

Origin = coxa joint.

### Step 1: Coxa yaw (α)

The coxa rotates horizontally about Z.  The yaw angle is simply the
horizontal bearing to the target:

```
α = atan2(y, x)
```

### Step 2: Horizontal reach past coxa

```
xy_dist = sqrt(x² + y²)
reach   = xy_dist − L_COXA
```

### Step 3: Triangle in the leg plane

After computing `reach` and `z`, we have a 2D triangle with sides:
- `L_FEMUR` (femur link)
- `L_TIBIA` (tibia link)
- `D = sqrt(reach² + z²)` (straight-line distance from femur pivot to foot)

### Step 4: Tibia interior angle (law of cosines)

```
cos(γ) = (L_FEMUR² + L_TIBIA² − D²) / (2 · L_FEMUR · L_TIBIA)
γ = acos(cos(γ))
```

### Step 5: Femur elevation angle

```
φ     = atan2(z, reach)          # angle of D vector
θ     = acos((Lf² + D² − Lt²) / (2·Lf·D))   # angle at femur pivot
β     = φ + θ                    # femur up from horizontal
```

### Reachability

```
|L_FEMUR − L_TIBIA| ≤ D ≤ L_FEMUR + L_TIBIA
```

If violated, `IKSolverError` is raised.

---

## Gait Engine State Machine

```
                ┌───────────────────────────────┐
                │          GaitEngine           │
                │                               │
                │  set_mode(STAND) ─────────┐  │
                │  set_mode(TRIPOD) ─────┐  │  │
                │  set_mode(WAVE) ───┐   │  │  │
                │  set_mode(RIPPLE)─┐│   │  │  │
                │                  ││   │  │  │
                │              RIPPLE WAVE TRIPOD STAND
                │                  │    │   │    │
                │               ───┴────┴───┴────┘
                │                  current_mode
                │
                │   tick(dt) → [6 × (coxa, femur, tibia)]
                │      │
                │      ├─ advance_legs(dt)
                │      │     ├─ SWINGING: parabolic XYZ arc
                │      │     └─ STANCE:  backward linear drag
                │      │
                │      └─ LegIK.solve(x, y, z) for each leg
                └───────────────────────────────┘
```

### Swing / Stance duty factors

| Gait | Legs swinging | Swing duty | Notes |
|---|---|---|---|
| Tripod | 3 ({0,2,4} or {1,3,5}) | 50 % | Fastest; always 3 legs on ground |
| Wave | 1 | ~17 % | Slowest; most stable; 5 legs on ground |
| Ripple | 2 | ~33 % | Balanced; 4 legs on ground |

---

## API Endpoint Reference

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| GET | `/status` | Full robot state JSON |
| POST | `/gait/{mode}` | Change gait: tripod / wave / ripple / stand / stop |
| POST | `/pose` | Body pose: `{pitch, roll, yaw_rate, height}` |
| POST | `/velocity` | Velocity: `{vx, vy, omega}` (m/s and deg/s) |
| POST | `/servo/{ch}/angle` | Manual servo override: `{angle}` |
| WS | `/ws/telemetry` | 10 Hz telemetry stream |
| GET | `/stream/video` | MJPEG video (vision service) |

---

## Data Flow

```
velocity input → GaitEngine.set_velocity()
                      │
              GaitEngine.tick(dt)
                      │
            for each leg: LegIK.solve(x, y, z)
                      │
                    angles[]
                      │
              PCA9685.set_all_servos()
                      │
                18 × PWM pulses
                      │
                 MG996R servos
```

Telemetry path (10 Hz):

```
MPU6050.read() + HC-SR04.scan()
        │
   JSON payload
        │
  WebSocket broadcast
        │
  Browser dashboard
```

---

## Configuration Reference

| Environment Variable | Default | Description |
|---|---|---|
| `I2C_BUS` | `1` | Linux I²C bus number |
| `PCA9685_ADDRESS` | `0x40` | PCA9685 I²C address (hex) |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `CAMERA_ENABLED` | `false` | Enable MJPEG video endpoint |
| `TICK_RATE_HZ` | `50` | Gait engine control loop frequency |
| `CAMERA_INDEX` | `0` | OpenCV camera device index (vision service) |
| `JPEG_QUALITY` | `80` | MJPEG JPEG quality 1–100 (vision service) |

---

## Development Workflow

```bash
# Run tests
pytest software/tests/ -v

# Lint
flake8 software/ && black --check software/

# Auto-format
black software/

# Start API in dev mode (hot-reload)
uvicorn hexapod_core.api.main:app --reload --port 8000

# Run via Docker Compose
docker compose up --build hexapod-core hexapod-ui

# Inspect running containers
docker compose logs -f hexapod-core
docker compose exec hexapod-core i2cdetect -y 1
```
