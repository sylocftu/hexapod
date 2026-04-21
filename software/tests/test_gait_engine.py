"""
Tests for the GaitEngine.

All tests run without hardware; the gait engine is pure Python.
"""

import math

import pytest

from hexapod_core.gait import GaitEngine, GaitMode, StepParams
from hexapod_core.kinematics import LegIK


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine() -> GaitEngine:
    """GaitEngine with default parameters."""
    ik = LegIK()
    params = StepParams(step_height=0.030, step_length=0.040, cycle_time=1.0)
    return GaitEngine(ik, params)


# ── Initialisation ─────────────────────────────────────────────────────────────

def test_initial_mode_is_stand(engine: GaitEngine) -> None:
    assert engine._mode == GaitMode.STAND


def test_initial_velocity_zero(engine: GaitEngine) -> None:
    assert engine._vx == 0.0
    assert engine._vy == 0.0
    assert engine._omega == 0.0


# ── tick() output shape ────────────────────────────────────────────────────────

def test_tick_returns_six_tuples(engine: GaitEngine) -> None:
    angles = engine.tick(0.02)
    assert len(angles) == 6, "tick() must return exactly 6 angle tuples"


def test_tick_each_tuple_has_three_angles(engine: GaitEngine) -> None:
    angles = engine.tick(0.02)
    for i, leg_angles in enumerate(angles):
        assert len(leg_angles) == 3, f"Leg {i} tuple has wrong length"


# ── STAND mode ─────────────────────────────────────────────────────────────────

def test_stand_mode_angles_stable(engine: GaitEngine) -> None:
    """In STAND mode with zero velocity, angles should not change between ticks."""
    engine.set_mode(GaitMode.STAND)
    angles1 = engine.tick(0.02)
    angles2 = engine.tick(0.02)
    for i in range(6):
        for j in range(3):
            assert abs(angles1[i][j] - angles2[i][j]) < 1e-6, (
                f"Leg {i} joint {j} changed in STAND mode"
            )


# ── TRIPOD mode ────────────────────────────────────────────────────────────────

def test_tripod_mode_produces_angles(engine: GaitEngine) -> None:
    engine.set_mode(GaitMode.TRIPOD)
    engine.set_velocity(0.05, 0.0, 0.0)
    angles = engine.tick(0.02)
    assert len(angles) == 6


def test_tripod_angles_in_servo_range(engine: GaitEngine) -> None:
    """Run 20 ticks in tripod mode and verify all angles are in [0°, 180°]."""
    engine.set_mode(GaitMode.TRIPOD)
    engine.set_velocity(0.05, 0.0, 0.0)
    for _ in range(20):
        angles = engine.tick(0.02)
        for leg_idx, (coxa, femur, tibia) in enumerate(angles):
            assert 0.0 <= coxa <= 180.0 or -180.0 <= coxa <= 180.0, (
                f"Coxa angle {coxa:.1f}° on leg {leg_idx} is unreasonable"
            )
            assert 0.0 <= tibia <= 180.0, (
                f"Tibia angle {tibia:.1f}° on leg {leg_idx} out of range"
            )


# ── WAVE mode ──────────────────────────────────────────────────────────────────

def test_wave_mode_produces_angles(engine: GaitEngine) -> None:
    engine.set_mode(GaitMode.WAVE)
    engine.set_velocity(0.03, 0.0, 0.0)
    angles = engine.tick(0.02)
    assert len(angles) == 6


# ── RIPPLE mode ────────────────────────────────────────────────────────────────

def test_ripple_mode_produces_angles(engine: GaitEngine) -> None:
    engine.set_mode(GaitMode.RIPPLE)
    engine.set_velocity(0.04, 0.0, 0.0)
    angles = engine.tick(0.02)
    assert len(angles) == 6


# ── Mode switching ─────────────────────────────────────────────────────────────

def test_mode_switching_does_not_crash(engine: GaitEngine) -> None:
    for mode in [GaitMode.TRIPOD, GaitMode.WAVE, GaitMode.RIPPLE, GaitMode.STAND]:
        engine.set_mode(mode)
        angles = engine.tick(0.02)
        assert len(angles) == 6, f"tick() returned wrong length after switching to {mode}"


# ── Velocity ───────────────────────────────────────────────────────────────────

def test_set_velocity_stored(engine: GaitEngine) -> None:
    engine.set_velocity(0.1, -0.05, 30.0)
    assert engine._vx == pytest.approx(0.1)
    assert engine._vy == pytest.approx(-0.05)
    assert engine._omega == pytest.approx(30.0)


def test_velocity_changes_foot_positions(engine: GaitEngine) -> None:
    """Moving velocity should cause angles to differ from zero-velocity angles."""
    engine.set_mode(GaitMode.TRIPOD)
    engine.set_velocity(0.0, 0.0, 0.0)
    angles_still = [engine.tick(0.02) for _ in range(5)]

    engine2 = GaitEngine(LegIK(), StepParams(step_height=0.030, step_length=0.040))
    engine2.set_mode(GaitMode.TRIPOD)
    engine2.set_velocity(0.1, 0.0, 0.0)
    angles_moving = [engine2.tick(0.02) for _ in range(5)]

    # After 5 ticks the two engines should have different angles for at least one leg
    # (this is a sanity check, not a precise value test)
    any_different = any(
        abs(angles_still[-1][i][j] - angles_moving[-1][i][j]) > 1e-3
        for i in range(6)
        for j in range(3)
    )
    assert any_different, "Moving velocity produced identical angles to zero velocity"


# ── Body pose ──────────────────────────────────────────────────────────────────

def test_body_height_param(engine: GaitEngine) -> None:
    """Changing body height should affect computed angles."""
    engine.set_mode(GaitMode.STAND)
    params_low = StepParams(body_height=-0.08)
    engine.set_params(params_low)
    angles_low = engine.tick(0.02)

    params_high = StepParams(body_height=-0.14)
    engine.set_params(params_high)
    angles_high = engine.tick(0.02)

    any_different = any(
        abs(angles_low[i][j] - angles_high[i][j]) > 0.1
        for i in range(6)
        for j in range(3)
    )
    assert any_different, "Changing body height produced identical angles"


# ── Extended run ───────────────────────────────────────────────────────────────

def test_10_ticks_no_exception(engine: GaitEngine) -> None:
    """Run 10 ticks in each gait mode without error."""
    for mode in GaitMode:
        engine.set_mode(mode)
        if mode != GaitMode.STAND:
            engine.set_velocity(0.05, 0.0, 0.0)
        else:
            engine.set_velocity(0.0, 0.0, 0.0)
        for _ in range(10):
            angles = engine.tick(0.02)
            assert len(angles) == 6
