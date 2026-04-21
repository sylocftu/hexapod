# 🕷️ STEM Hexapod Robot

A fully open-source, 3D-printed, 6-legged spider robot designed for STEM education.
The hexapod features **18 servos** (3 degrees of freedom per leg), a Raspberry Pi 4 brain,
real-time inverse kinematics, multiple gait modes, and a browser-based control dashboard.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Hardware Requirements](#hardware-requirements)
3. [3D Printing](#3d-printing)
4. [Software Architecture](#software-architecture)
5. [Quick Start (Docker)](#quick-start-docker)
6. [Development Setup](#development-setup)
7. [Contributing](#contributing)
8. [License](#license)

---

## Project Overview

| Feature | Detail |
|---|---|
| Legs | 6 |
| DOF per leg | 3 (coxa / femur / tibia) |
| Total servos | 18 × MG996R |
| Controller | Raspberry Pi 4 (4 GB) |
| Servo driver | PCA9685 (I²C) |
| IMU | MPU-6050 |
| Distance sensors | 3 × HC-SR04 (front/left/right) |
| Camera | Raspberry Pi Camera Module v2 |
| Power | 7.4 V 2-cell LiPo, dual BEC regulators |
| Gaits | Tripod · Wave · Ripple · Stand |
| API | FastAPI REST + WebSocket |
| Dashboard | Vanilla JS single-page app |

The robot can be tele-operated via the web dashboard or run autonomously using the
obstacle-avoidance mode.  All source code is written to be readable by high-school
STEM students.

---

## Hardware Requirements

See [`hardware/bom.csv`](hardware/bom.csv) for a full bill of materials with costs and suppliers.

Key components:

- **Raspberry Pi 4** (4 GB RAM recommended)
- **PCA9685** 16-channel PWM servo driver board
- **18 × MG996R** metal-gear servos
- **7.4 V LiPo** battery (5000 mAh minimum)
- **MPU-6050** 6-axis IMU
- **3 × HC-SR04** ultrasonic sensors

Wiring instructions are in [`hardware/wiring_notes.md`](hardware/wiring_notes.md).
Schematic source files (KiCad) live in [`hardware/schematics/`](hardware/schematics/).

---

## 3D Printing

All printable parts are described in [`cad/README.md`](cad/README.md).
Recommended slicer settings are in [`cad/print_settings.md`](cad/print_settings.md).
Export STL files from FreeCAD and place them in [`cad/stl/`](cad/stl/).

**Estimated print time:** ~35 hours total on a 0.4 mm nozzle printer.

---

## Software Architecture

See [`docs/software_architecture.md`](docs/software_architecture.md) for a full description.

```
┌─────────────────────────────────────────────────┐
│               Browser Dashboard (UI)            │
│          index.html / app.js / style.css        │
└───────────────────┬─────────────────────────────┘
                    │ HTTP / WebSocket
┌───────────────────▼─────────────────────────────┐
│            FastAPI Core Service                 │
│         hexapod_core.api.main  :8000            │
├──────────────┬──────────────────────────────────┤
│  Gait Engine │  IK Solver  │  Hardware Drivers  │
│  gait_engine │  ik_solver  │  pca9685 / imu /   │
│              │             │  sensors            │
└──────────────┴─────────────┴────────────────────┘
                    │ I²C / GPIO
┌───────────────────▼─────────────────────────────┐
│           Raspberry Pi 4 Hardware               │
│    PCA9685 → 18 servos   MPU-6050   HC-SR04×3   │
└─────────────────────────────────────────────────┘
```

---

## Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/your-org/hexapod.git
cd hexapod

# Start core + UI services (runs on Pi or any Linux host)
docker compose up -d hexapod-core hexapod-ui

# Open dashboard in browser
open http://localhost

# (Optional) Start vision service
docker compose --profile vision up -d hexapod-vision

# View logs
docker compose logs -f hexapod-core

# Stop everything
docker compose down
```

> **Hardware note:** On a Raspberry Pi the containers need `privileged: true`
> and access to `/dev/i2c-1` and `/dev/gpiomem`.  On a desktop the services
> run in simulation mode automatically.

---

## Development Setup

```bash
# 1. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies (skip RPi-specific packages on non-Pi)
pip install -r software/requirements.txt

# 3. Install the package in editable mode
pip install -e software/

# 4. Run tests
pytest software/tests/ -v

# 5. Start the API in dev mode (simulation, no hardware required)
uvicorn hexapod_core.api.main:app --reload --port 8000

# 6. Open the UI
# Just open software/ui/index.html in your browser (or serve with any static server)
python3 -m http.server 8080 --directory software/ui
```

---

## STEM Worksheets

Five educational worksheets in [`docs/stem_worksheets/`](docs/stem_worksheets/) cover:

1. What is a hexapod? (biology + robotics)
2. Trigonometry and Inverse Kinematics
3. Gait Patterns and Timing
4. Sensors and Obstacle Avoidance
5. Docker and DevOps

---

## Contributing

1. Fork the repository and create a feature branch.
2. Ensure `flake8` and `black` pass: `flake8 software/ && black --check software/`
3. Add or update tests for any changed behaviour.
4. Open a Pull Request with a clear description.

Please read [`docs/software_architecture.md`](docs/software_architecture.md) before
making changes to the IK solver or gait engine.

---

## License

MIT License © 2024 STEM Hexapod Project Contributors.

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT.
