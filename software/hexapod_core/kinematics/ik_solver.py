"""
Analytic 3-DOF Inverse Kinematics solver for a hexapod leg.

Leg coordinate system
---------------------
- Origin at the coxa joint (body attachment point).
- X axis points forward along the leg plane (outward from body).
- Z axis points up.

Joints (proximal → distal)
--------------------------
1. Coxa  – horizontal rotation about Z (yaw,   α)  range: [-90°, +90°]
2. Femur – vertical   rotation about Y (pitch,  β)  range: [-90°, +90°]
3. Tibia – vertical   rotation about Y (elbow,  γ)  range: [  0°, +150°]

Link lengths (metres, configurable)
------------------------------------
L_COXA  = 0.052  # 52 mm  — hip to first knee
L_FEMUR = 0.080  # 80 mm  — first knee to second knee
L_TIBIA = 0.120  # 120 mm — second knee to foot tip

Derivation overview
-------------------
1. α = atan2(y, x)                          — coxa yaw from target XY
2. Project target into the leg plane to get (r, z):
       r = sqrt(x² + y²) - L_COXA          — horizontal reach past coxa
3. Use the law of cosines on the femur–tibia–target triangle:
       D = sqrt(r² + z²)                    — distance from femur pivot to foot
       cos(γ) = (L_FEMUR² + L_TIBIA² - D²) / (2·L_FEMUR·L_TIBIA)
       γ = acos(...)                        — tibia angle (interior angle)
4. β  = atan2(z, r) - atan2(L_TIBIA·sin(γ), L_FEMUR + L_TIBIA·cos(γ))
"""

import math

# Default link lengths (metres)
L_COXA: float = 0.052
L_FEMUR: float = 0.080
L_TIBIA: float = 0.120


class IKSolverError(Exception):
    """Raised when the requested foot position is outside the leg's workspace."""


class LegIK:
    """Analytic inverse-kinematics solver for a single 3-DOF hexapod leg.

    Parameters
    ----------
    l_coxa, l_femur, l_tibia : float
        Link lengths in metres.
    """

    def __init__(
        self,
        l_coxa: float = L_COXA,
        l_femur: float = L_FEMUR,
        l_tibia: float = L_TIBIA,
    ) -> None:
        if any(l <= 0 for l in (l_coxa, l_femur, l_tibia)):
            raise ValueError("All link lengths must be positive.")
        self.l_coxa = l_coxa
        self.l_femur = l_femur
        self.l_tibia = l_tibia

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def solve(self, x: float, y: float, z: float) -> tuple:
        """Compute joint angles for foot position (x, y, z).

        Parameters
        ----------
        x, y, z : float
            Target foot position in metres relative to the coxa joint.
            Positive x is forward, positive y is left, positive z is up.

        Returns
        -------
        (coxa_deg, femur_deg, tibia_deg) : tuple[float, float, float]
            Joint angles in degrees.
            Coxa: measured from forward axis (positive = CCW viewed from above).
            Femur: measured from horizontal (positive = up).
            Tibia: interior angle at knee (0° = straight, positive = bent).

        Raises
        ------
        IKSolverError
            When the target is outside the reachable workspace.
        """
        # ── Step 1: Coxa yaw (α) ──────────────────────────────────────
        # α is simply the horizontal bearing to the target.
        alpha_rad = math.atan2(y, x)

        # Horizontal distance from coxa joint to foot projection on XY plane
        xy_dist = math.hypot(x, y)

        # Reach from the femur pivot (after subtracting coxa link length)
        reach = xy_dist - self.l_coxa

        # ── Step 2: Check workspace ───────────────────────────────────
        # Distance from femur pivot to foot
        d = math.hypot(reach, z)

        max_reach = self.l_femur + self.l_tibia
        min_reach = abs(self.l_femur - self.l_tibia)

        if d > max_reach:
            raise IKSolverError(
                f"Target ({x:.4f}, {y:.4f}, {z:.4f}) is too far: "
                f"D={d:.4f} m > max_reach={max_reach:.4f} m."
            )
        if d < min_reach:
            raise IKSolverError(
                f"Target ({x:.4f}, {y:.4f}, {z:.4f}) is too close: "
                f"D={d:.4f} m < min_reach={min_reach:.4f} m."
            )

        # ── Step 3: Tibia interior angle (γ) via law of cosines ───────
        # Law of cosines: D² = L_FEMUR² + L_TIBIA² - 2·Lf·Lt·cos(π - γ)
        # Rearranged for interior angle γ:
        cos_gamma = (
            (self.l_femur ** 2 + self.l_tibia ** 2 - d ** 2)
            / (2.0 * self.l_femur * self.l_tibia)
        )
        # Clamp to [-1, 1] to guard against floating-point drift
        cos_gamma = max(-1.0, min(1.0, cos_gamma))
        gamma_rad = math.acos(cos_gamma)  # interior knee angle

        # ── Step 4: Femur elevation angle (β) ─────────────────────────
        # Angle of the D vector below/above horizontal
        phi = math.atan2(z, reach)
        # Angle of femur relative to D vector (from law of sines)
        cos_theta = (
            (self.l_femur ** 2 + d ** 2 - self.l_tibia ** 2)
            / (2.0 * self.l_femur * d)
        )
        cos_theta = max(-1.0, min(1.0, cos_theta))
        theta_rad = math.acos(cos_theta)

        beta_rad = phi + theta_rad  # femur up = positive

        # ── Convert to degrees ────────────────────────────────────────
        coxa_deg = math.degrees(alpha_rad)
        femur_deg = math.degrees(beta_rad)
        tibia_deg = math.degrees(gamma_rad)

        return (coxa_deg, femur_deg, tibia_deg)

    def forward(self, coxa_deg: float, femur_deg: float, tibia_deg: float) -> tuple:
        """Compute foot (x, y, z) from joint angles (forward kinematics).

        Used to validate solve() and to animate the 3D view.

        Parameters
        ----------
        coxa_deg, femur_deg, tibia_deg : float
            Joint angles in degrees (same convention as solve() returns).

        Returns
        -------
        (x, y, z) : tuple[float, float, float]
            Foot position in metres relative to the coxa joint.
        """
        alpha = math.radians(coxa_deg)
        beta = math.radians(femur_deg)
        gamma = math.radians(tibia_deg)

        # Length from femur pivot to foot tip along the leg plane
        # The tibia interior angle γ is the angle at the knee; the exterior
        # angle that continues the femur direction is (π - γ).
        # Position relative to femur pivot (in the leg plane, forward/up):
        leg_plane_x = (
            self.l_femur * math.cos(beta)
            + self.l_tibia * math.cos(beta - (math.pi - gamma))
        )
        leg_plane_z = (
            self.l_femur * math.sin(beta)
            + self.l_tibia * math.sin(beta - (math.pi - gamma))
        )

        # Add coxa offset; project out of leg plane using coxa yaw
        xy_reach = self.l_coxa + leg_plane_x
        x = xy_reach * math.cos(alpha)
        y = xy_reach * math.sin(alpha)
        z = leg_plane_z

        return (x, y, z)
