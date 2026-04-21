"""
Gait engine for hexapod locomotion.

Supported gaits
---------------
- tripod  : legs {0,2,4} swing while {1,3,5} stance (fastest, least stable)
- wave    : one leg at a time, sequential 0→5 (slowest, most stable)
- ripple  : two legs at a time in overlapping phases (balanced)
- stand   : all legs in default neutral stance (stationary)

Leg numbering (top view, front of robot at top)
-----------------------------------------------
     FRONT
  Leg0   Leg1
Leg2       Leg3
  Leg4   Leg5
      BACK

Each leg has a default neutral foot position (x0, y0, z0) defined
relative to the body centre.  x = forward, y = left, z = up.

The engine generates swing/stance trajectories and calls LegIK for each
leg at every control tick.  All computations are pure Python / NumPy;
no hardware imports.
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from hexapod_core.kinematics import LegIK

# ── Gait constants ─────────────────────────────────────────────────────────────

# Tripod groups: A swings while B stances, then swap
_TRIPOD_A = (0, 2, 4)
_TRIPOD_B = (1, 3, 5)

# Wave gait: one leg swings at a time, 0→5
_WAVE_ORDER = (0, 2, 4, 5, 3, 1)  # left front→mid→rear then right rear→mid→front

# Ripple: two legs at a time, 120° phase-shifted pairs
_RIPPLE_GROUPS = ((0, 3), (2, 5), (4, 1))

# Neutral foot positions (metres, relative to body centre).
# Arranged at 90 mm radius with ±30° offset from pure lateral.
_BODY_RADIUS = 0.090  # 90 mm

# Leg angular positions (radians, measured from forward = 0)
_LEG_ANGLES_RAD = [
    math.radians(ang) for ang in (45, -45, 90, -90, 135, -135)
]

# Default body height above ground
_DEFAULT_HEIGHT = -0.10  # 10 cm below coxa plane (negative z = down)


def _default_neutral_positions() -> List[Tuple[float, float, float]]:
    """Compute the 6 neutral foot positions at body height."""
    positions = []
    for ang in _LEG_ANGLES_RAD:
        x0 = _BODY_RADIUS * math.cos(ang)
        y0 = _BODY_RADIUS * math.sin(ang)
        z0 = _DEFAULT_HEIGHT
        positions.append((x0, y0, z0))
    return positions


# ── Data classes ───────────────────────────────────────────────────────────────


class GaitMode(Enum):
    """Available locomotion modes."""

    TRIPOD = "tripod"
    WAVE = "wave"
    RIPPLE = "ripple"
    STAND = "stand"


@dataclass
class StepParams:
    """Parameters controlling step shape and timing."""

    step_height: float = 0.040      # swing arc height in metres
    step_length: float = 0.050      # max stride length in metres
    cycle_time: float = 1.0         # full gait cycle duration in seconds
    body_height: float = -0.10      # body height relative to coxa plane (m)
    # Body pose offsets (applied every tick)
    roll: float = 0.0               # degrees
    pitch: float = 0.0              # degrees
    yaw_rate: float = 0.0           # body yaw rate deg/s (stationary rotation)


# ── Leg state ─────────────────────────────────────────────────────────────────


@dataclass
class _LegState:
    """Internal per-leg state tracked by the gait engine."""

    neutral: Tuple[float, float, float]  # neutral foot position
    current: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    phase: float = 0.0              # phase within gait cycle [0, 1)
    is_swinging: bool = False


# ── GaitEngine ────────────────────────────────────────────────────────────────


class GaitEngine:
    """Hexapod gait engine.

    Parameters
    ----------
    ik_solver : LegIK
        Inverse kinematics solver instance (shared by all legs).
    params : StepParams
        Initial step parameters.
    """

    def __init__(
        self,
        ik_solver: LegIK,
        params: Optional[StepParams] = None,
    ) -> None:
        self._ik = ik_solver
        self._params = params or StepParams()
        self._mode = GaitMode.STAND
        self._vx: float = 0.0   # forward velocity (m/s)
        self._vy: float = 0.0   # lateral velocity (m/s)
        self._omega: float = 0.0  # yaw rate (deg/s)

        # Initialise leg states
        neutrals = _default_neutral_positions()
        self._legs: List[_LegState] = []
        for i, n in enumerate(neutrals):
            ls = _LegState(neutral=n)
            ls.current = list(n)
            # Stagger initial phases so legs start at different points
            ls.phase = 0.0
            self._legs.append(ls)

        # Assign initial swing phases based on gait groups
        self._assign_phases()

        # Elapsed time accumulator
        self._t: float = 0.0

    # ── Public interface ───────────────────────────────────────────────────────

    def set_mode(self, mode: GaitMode) -> None:
        """Switch gait mode.  Resets leg phases to avoid jumps."""
        self._mode = mode
        self._assign_phases()
        self._t = 0.0

    def set_velocity(self, vx: float, vy: float, omega: float) -> None:
        """Set desired body velocity.

        Parameters
        ----------
        vx : float  Forward velocity in m/s  (positive = forward)
        vy : float  Lateral velocity in m/s  (positive = left)
        omega : float  Yaw rate in deg/s     (positive = CCW from above)
        """
        self._vx = vx
        self._vy = vy
        self._omega = omega

    def set_params(self, params: StepParams) -> None:
        """Update step parameters."""
        self._params = params

    def tick(self, dt: float) -> List[Tuple[float, float, float]]:
        """Advance the gait by `dt` seconds and return servo angles.

        Parameters
        ----------
        dt : float
            Time step in seconds.

        Returns
        -------
        list of 6 (coxa_deg, femur_deg, tibia_deg) tuples — one per leg.
        """
        self._t += dt
        p = self._params

        # Update body height from params
        for ls in self._legs:
            nx, ny, _ = ls.neutral
            ls.neutral = (nx, ny, p.body_height)

        angles: List[Tuple[float, float, float]] = []

        if self._mode == GaitMode.STAND:
            # All legs at neutral, no motion
            for ls in self._legs:
                ls.current = list(ls.neutral)
        else:
            self._advance_legs(dt, p)

        # Compute IK for each leg
        for ls in self._legs:
            cx, cy, cz = ls.current
            # Apply body rotation to foot position (yaw body offset)
            cx, cy = self._apply_body_yaw(cx, cy, dt)
            try:
                ang = self._ik.solve(cx, cy, cz)
            except Exception:
                # Fall back to neutral on IK failure
                ang = self._ik.solve(*ls.neutral)
            angles.append(ang)

        return angles

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _assign_phases(self) -> None:
        """Set initial phase for each leg based on the current gait mode."""
        if self._mode == GaitMode.TRIPOD:
            for i in _TRIPOD_A:
                self._legs[i].phase = 0.0
            for i in _TRIPOD_B:
                self._legs[i].phase = 0.5
        elif self._mode == GaitMode.WAVE:
            for idx, leg in enumerate(_WAVE_ORDER):
                self._legs[leg].phase = idx / 6.0
        elif self._mode == GaitMode.RIPPLE:
            for g_idx, group in enumerate(_RIPPLE_GROUPS):
                phase_offset = g_idx / 3.0
                for leg in group:
                    self._legs[leg].phase = phase_offset
        else:  # STAND
            for ls in self._legs:
                ls.phase = 0.0

    def _advance_legs(self, dt: float, p: StepParams) -> None:
        """Update all leg positions for one time step."""
        # Determine swing duty factor per gait
        if self._mode == GaitMode.TRIPOD:
            swing_duty = 0.5   # 50 % of cycle is swing
        elif self._mode == GaitMode.WAVE:
            swing_duty = 1.0 / 6.0   # ~17 % swing
        else:  # RIPPLE
            swing_duty = 1.0 / 3.0   # ~33 % swing

        phase_advance = dt / p.cycle_time if p.cycle_time > 0 else 0.0

        # Compute per-leg velocity contribution from body motion
        # In stance: foot moves opposite to body velocity (ground contact)
        # In swing: foot moves to new target position
        moving = abs(self._vx) > 1e-4 or abs(self._vy) > 1e-4

        for ls in self._legs:
            old_phase = ls.phase
            ls.phase = (ls.phase + phase_advance) % 1.0
            was_swinging = old_phase < swing_duty
            now_swinging = ls.phase < swing_duty

            nx, ny, nz = ls.neutral

            if now_swinging:
                # Swing trajectory: parabolic Z arc, linear XY toward target
                swing_phase = ls.phase / swing_duty   # 0→1 within swing
                # Target: neutral + forward step
                if moving:
                    tx = nx + self._vx * p.step_length / max(abs(self._vx) + abs(self._vy), 1e-4)
                    ty = ny + self._vy * p.step_length / max(abs(self._vx) + abs(self._vy), 1e-4)
                else:
                    tx, ty = nx, ny

                # Start position (where foot was at start of swing)
                sx, sy = ls.current[0], ls.current[1]

                # Linear interpolation in XY
                ls.current[0] = sx + (tx - sx) * swing_phase
                ls.current[1] = sy + (ty - sy) * swing_phase

                # Parabolic arc in Z: z = nz + h·4·t·(1-t)
                ls.current[2] = nz + p.step_height * 4.0 * swing_phase * (1.0 - swing_phase)
            else:
                # Stance: drag foot backward (opposite to body motion)
                if moving:
                    ls.current[0] -= self._vx * dt
                    ls.current[1] -= self._vy * dt
                ls.current[2] = nz

    def _apply_body_yaw(self, x: float, y: float, dt: float) -> Tuple[float, float]:
        """Rotate foot position by accumulated body yaw offset."""
        if abs(self._omega) < 1e-4:
            return x, y
        # Rotate the foot position relative to body centre
        angle_rad = math.radians(self._omega * dt)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        xr = x * cos_a - y * sin_a
        yr = x * sin_a + y * cos_a
        return xr, yr
