"""
Comprehensive tests for the LegIK inverse kinematics solver.

All tests run without any hardware; the solver is pure Python / math.
"""

import math

import pytest

from hexapod_core.kinematics import IKSolverError, LegIK, L_COXA, L_FEMUR, L_TIBIA


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def ik() -> LegIK:
    """Default LegIK instance with standard link lengths."""
    return LegIK()


@pytest.fixture
def ik_small() -> LegIK:
    """LegIK with smaller link lengths for edge-case testing."""
    return LegIK(l_coxa=0.030, l_femur=0.050, l_tibia=0.080)


# ── Constructor tests ─────────────────────────────────────────────────────────

def test_default_link_lengths(ik: LegIK) -> None:
    assert ik.l_coxa == L_COXA
    assert ik.l_femur == L_FEMUR
    assert ik.l_tibia == L_TIBIA


def test_invalid_link_length_raises() -> None:
    with pytest.raises(ValueError):
        LegIK(l_coxa=-0.01, l_femur=0.08, l_tibia=0.12)

    with pytest.raises(ValueError):
        LegIK(l_coxa=0.05, l_femur=0.0, l_tibia=0.12)


# ── Solve — reachable positions ───────────────────────────────────────────────

@pytest.mark.parametrize("x, y, z", [
    (0.15,  0.00, -0.08),   # forward, centred, moderate depth
    (0.10,  0.05, -0.10),   # forward-left, deep
    (0.12, -0.04, -0.06),   # forward-right, shallow
    (0.08,  0.00, -0.12),   # forward, very deep
    (0.18,  0.00, -0.05),   # long reach, shallow
])
def test_solve_returns_three_angles(ik: LegIK, x: float, y: float, z: float) -> None:
    result = ik.solve(x, y, z)
    assert len(result) == 3, "solve() must return exactly three angles"


@pytest.mark.parametrize("x, y, z", [
    (0.15,  0.00, -0.08),
    (0.10,  0.05, -0.10),
    (0.12, -0.04, -0.06),
])
def test_solve_angles_in_plausible_range(ik: LegIK, x: float, y: float, z: float) -> None:
    coxa, femur, tibia = ik.solve(x, y, z)
    # Coxa is a yaw angle — should be in [-180, 180]
    assert -180.0 <= coxa <= 180.0, f"Coxa angle {coxa} out of range"
    # Tibia is an interior knee angle — physically [0, 180]
    assert 0.0 <= tibia <= 180.0, f"Tibia angle {tibia} out of range"


# ── Round-trip: solve → forward (within 1 mm tolerance) ──────────────────────

@pytest.mark.parametrize("x, y, z", [
    (0.15,  0.00, -0.08),
    (0.10,  0.05, -0.10),
    (0.12, -0.04, -0.06),
    (0.08,  0.08, -0.09),
    (0.18,  0.00, -0.05),
    (0.10,  0.00, -0.15),
])
def test_round_trip_within_1mm(ik: LegIK, x: float, y: float, z: float) -> None:
    """Solving then running forward kinematics should reproduce the original point."""
    coxa, femur, tibia = ik.solve(x, y, z)
    rx, ry, rz = ik.forward(coxa, femur, tibia)

    tolerance = 0.001  # 1 mm
    assert abs(rx - x) < tolerance, f"FK x error: {abs(rx - x):.5f} m"
    assert abs(ry - y) < tolerance, f"FK y error: {abs(ry - y):.5f} m"
    assert abs(rz - z) < tolerance, f"FK z error: {abs(rz - z):.5f} m"


# ── Unreachable positions raise IKSolverError ─────────────────────────────────

def test_too_far_raises(ik: LegIK) -> None:
    max_reach = ik.l_coxa + ik.l_femur + ik.l_tibia
    with pytest.raises(IKSolverError):
        ik.solve(max_reach + 0.05, 0.0, 0.0)


def test_too_close_raises(ik: LegIK) -> None:
    # Position exactly at coxa origin is unreachable (femur/tibia would need to fold back)
    with pytest.raises(IKSolverError):
        ik.solve(ik.l_coxa, 0.0, 0.0)


def test_negative_reach_raises(ik: LegIK) -> None:
    # Far behind the coxa joint — xy_dist=0.40, reach=0.348 > max_reach=0.20
    with pytest.raises(IKSolverError):
        ik.solve(-0.40, 0.0, 0.0)


# ── Neutral stance position (directly below, centred) ─────────────────────────

def test_neutral_stance(ik: LegIK) -> None:
    """
    Neutral stance: foot directly forward of coxa, Z below.
    Coxa angle should be ~0°.
    """
    x = 0.14
    y = 0.0
    z = -0.09
    coxa, femur, tibia = ik.solve(x, y, z)
    assert abs(coxa) < 1.0, f"Expected coxa ≈ 0°, got {coxa:.2f}°"


# ── Zero lateral offset ───────────────────────────────────────────────────────

def test_zero_y(ik: LegIK) -> None:
    """Zero lateral offset → coxa angle should be zero."""
    coxa, _, _ = ik.solve(0.15, 0.0, -0.08)
    assert abs(coxa) < 1e-9, f"Expected coxa = 0°, got {coxa}"


def test_positive_y_coxa_positive(ik: LegIK) -> None:
    """Positive y → positive coxa yaw."""
    coxa, _, _ = ik.solve(0.12, 0.06, -0.08)
    assert coxa > 0.0, f"Expected positive coxa, got {coxa}"


def test_negative_y_coxa_negative(ik: LegIK) -> None:
    """Negative y → negative coxa yaw."""
    coxa, _, _ = ik.solve(0.12, -0.06, -0.08)
    assert coxa < 0.0, f"Expected negative coxa, got {coxa}"


# ── Forward kinematics standalone ─────────────────────────────────────────────

def test_forward_straight(ik: LegIK) -> None:
    """At 0° coxa, 0° femur, 180° tibia (fully extended) the foot should be at
    x = L_coxa + L_femur + L_tibia, y = 0, z = 0."""
    # tibia interior angle of 180° means the tibia extends straight (no bend).
    x, y, z = ik.forward(0.0, 0.0, 180.0)
    expected_x = ik.l_coxa + ik.l_femur + ik.l_tibia
    assert abs(x - expected_x) < 1e-6, f"Expected x≈{expected_x:.4f}, got {x:.4f}"
    assert abs(y) < 1e-9, f"Expected y=0, got {y}"
