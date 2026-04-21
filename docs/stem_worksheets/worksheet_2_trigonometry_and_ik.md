# Worksheet 2: Trigonometry and Inverse Kinematics

**Subject:** Mathematics + Robotics  
**Grade level:** 9–12  
**Estimated time:** 60 minutes  
**Prerequisite knowledge:** Basic trigonometry (sin, cos, tan, Pythagoras)

---

## Learning Objectives

By the end of this worksheet, you will be able to:

1. Explain the difference between **forward kinematics** and **inverse kinematics**.
2. Derive the coxa yaw angle using `atan2`.
3. Apply the **law of cosines** to find femur and tibia angles.
4. Use the `LegIK` class in Python to compute servo angles for a given foot position.
5. Describe the concept of a *reachable workspace*.

---

## Background: Forward vs. Inverse Kinematics

There are two fundamental problems in robot arm/leg control:

**Forward Kinematics (FK):** Given joint angles, where is the foot?  
`angles → position`

**Inverse Kinematics (IK):** Given a desired foot position, what angles do we need?  
`position → angles`

FK is easy — we just follow the chain of rotations.  
IK is harder because the same position may have zero, one, or many solutions.

For our 3-DOF leg the solution is **analytic** (a closed-form formula),
which is much faster than numeric methods.

---

## Coordinate System

```
         Z (up)
         │
         │   foot target (x, y, z)
         │         ╱
         │        ╱
         └───────────────── X (forward)
        ╱
       Y (left)

Origin = coxa joint (body attachment point)
```

Link lengths:
- `L_COXA  = 52 mm`  (hip to first knee)
- `L_FEMUR = 80 mm`  (first knee to second knee)
- `L_TIBIA = 120 mm` (second knee to foot tip)

---

## Step 1: Coxa Yaw Angle (α)

The coxa joint rotates horizontally about the Z axis (like turning your hip left/right).

Looking from above, the foot target is at position (x, y):

```
         Y (left)
         │     ╱ foot target
         │    ╱  at (x, y)
         │   ╱
         │  ╱← α (coxa angle)
         │ ╱
         └──────────── X (forward)
```

**Formula:**
$$\alpha = \text{atan2}(y, x)$$

`atan2(y, x)` returns the angle in radians of the point (x, y) from the positive X axis.
It handles all four quadrants correctly (unlike `atan(y/x)` which fails when x ≤ 0).

**Exercise 2.1:** Calculate α for the following targets.  Use a calculator.  
Convert your answer from radians to degrees (multiply by 180/π).

| Target (x, y) | α (radians) | α (degrees) |
|---|---|---|
| (0.15, 0.00) | _______ | _______ |
| (0.10, 0.10) | _______ | _______ |
| (0.00, 0.12) | _______ | _______ |
| (0.10, -0.05) | _______ | _______ |

---

## Step 2: Horizontal Reach

After the coxa rotates by angle α, the femur pivot is `L_COXA` away from the origin
along the direction α.  The remaining horizontal distance to the foot target is:

```
xy_dist = sqrt(x² + y²)     (total horizontal distance)
reach   = xy_dist − L_COXA  (horizontal distance from femur pivot to foot)
```

**Exercise 2.2:** For target (0.15, 0.00, -0.08):

```
xy_dist = ____________ m
reach   = ____________ m   (subtract L_COXA = 0.052 m)
```

---

## Step 3: The Leg Plane Triangle

Now we look at the leg from the **side** (in the plane of the leg):

```
   Femur pivot (origin of triangle)
       │
       │  L_FEMUR = 0.080 m
       │         ╲
       │          ╲← γ (knee angle)
       │           ╲
       │            ● Tibia end
       │           ╱  L_TIBIA = 0.120 m
       │          ╱
       │         ╱
       │        ● Foot tip
```

In our 2D side view:
- Horizontal axis: `reach` (away from body)
- Vertical axis: `z` (up is positive)
- D = straight-line distance from femur pivot to foot tip

$$D = \sqrt{\text{reach}^2 + z^2}$$

**Exercise 2.3:** For reach = 0.098 m, z = -0.08 m:

```
D = ____________ m
```

---

## Step 4: Law of Cosines — Tibia Angle (γ)

The Law of Cosines states:
$$c^2 = a^2 + b^2 - 2ab\cos(C)$$

In our triangle (sides L_FEMUR, L_TIBIA, D; angle γ at femur–tibia joint):

$$D^2 = L_F^2 + L_T^2 - 2 \cdot L_F \cdot L_T \cdot \cos(\pi - \gamma)$$

Rearranging for the interior knee angle γ:

$$\cos(\gamma) = \frac{L_F^2 + L_T^2 - D^2}{2 \cdot L_F \cdot L_T}$$

$$\gamma = \arccos\!\left(\frac{L_F^2 + L_T^2 - D^2}{2 \cdot L_F \cdot L_T}\right)$$

**Exercise 2.4:** Use D from Exercise 2.3, L_F = 0.080 m, L_T = 0.120 m.

$$\cos(\gamma) = \frac{\_\_\_\_ + \_\_\_\_ - \_\_\_\_}{2 \times \_\_\_\_ \times \_\_\_\_} = \_\_\_\_$$

$$\gamma = \arccos(\_\_\_\_) = \_\_\_\_ \text{ radians} = \_\_\_\_ °$$

---

## Step 5: Femur Angle (β)

The femur elevation angle has two parts:

1. **φ** — the angle of the D vector below/above horizontal:
$$\phi = \text{atan2}(z, \text{reach})$$

2. **θ** — the angle between D and the femur (from law of cosines):
$$\cos(\theta) = \frac{L_F^2 + D^2 - L_T^2}{2 \cdot L_F \cdot D}$$

Combined:
$$\beta = \phi + \theta$$

**Exercise 2.5:** Complete the femur angle calculation:

$$\phi = \text{atan2}(-0.08, \_\_\_\_) = \_\_\_\_ °$$

$$\theta = \arccos\!\left(\frac{\_\_\_\_ + \_\_\_\_ - \_\_\_\_}{2 \times \_\_\_\_ \times \_\_\_\_}\right) = \_\_\_\_ °$$

$$\beta = \_\_\_\_ + \_\_\_\_ = \_\_\_\_ °$$

---

## Step 6: Reachable Workspace

The foot can only be reached if D (femur pivot to foot) satisfies:

$$|L_F - L_T| \leq D \leq L_F + L_T$$

**Exercise 2.6:**

Maximum reach (fully extended): _______ m  
Minimum reach (fully folded): _______ m  
Is (x=0.15, y=0, z=-0.08) reachable? _______ (show calculation)

---

## Python Exercise: Using LegIK

Open a Python terminal on your computer or Raspberry Pi.  
Ensure `hexapod-core` is installed: `pip install -e /path/to/software/`

```python
from hexapod_core.kinematics import LegIK

ik = LegIK()  # uses default link lengths

# Task: Solve IK for the foot directly forward and 10 cm below coxa
coxa, femur, tibia = ik.solve(x=0.15, y=0.0, z=-0.10)
print(f"Coxa:  {coxa:.1f}°")
print(f"Femur: {femur:.1f}°")
print(f"Tibia: {tibia:.1f}°")

# Task: Verify with forward kinematics
fx, fy, fz = ik.forward(coxa, femur, tibia)
print(f"FK result: ({fx:.4f}, {fy:.4f}, {fz:.4f}) m")
```

**Record your results:**

| Variable | Value |
|---|---|
| Coxa angle | _______ ° |
| Femur angle | _______ ° |
| Tibia angle | _______ ° |
| FK x | _______ m |
| FK y | _______ m |
| FK z | _______ m |
| Error (FK vs target) | _______ mm |

---

## Challenge: Map the Reachable Workspace

```python
import numpy as np
import matplotlib.pyplot as plt
from hexapod_core.kinematics import LegIK, IKSolverError

ik = LegIK()
reachable_x, reachable_z = [], []

for x in np.arange(0.05, 0.26, 0.005):
    for z in np.arange(-0.20, 0.05, 0.005):
        try:
            ik.solve(x, 0.0, z)
            reachable_x.append(x * 1000)   # convert to mm
            reachable_z.append(z * 1000)
        except IKSolverError:
            pass

plt.figure(figsize=(8, 5))
plt.scatter(reachable_x, reachable_z, s=1, c='blue')
plt.xlabel('X reach (mm)')
plt.ylabel('Z height (mm)')
plt.title('Reachable Workspace (side view, y=0)')
plt.axhline(0, color='grey', linestyle='--')
plt.grid(True)
plt.show()
```

**Questions:**
1. What shape is the reachable workspace?
2. How does doubling L_FEMUR change the shape?
3. Is the workspace symmetric about z = 0?

---

## Vocabulary List

| Term | Definition |
|---|---|
| Forward kinematics | Computing end-effector position from joint angles |
| Inverse kinematics (IK) | Computing joint angles from desired end-effector position |
| atan2(y, x) | Two-argument arctangent; returns angle in correct quadrant |
| Law of cosines | Generalisation of Pythagoras for any triangle |
| Interior angle | Angle measured inside the triangle |
| Reachable workspace | Set of all positions the foot can reach |
| Analytic solution | Closed-form formula (as opposed to iterative/numeric) |
| Singularity | A configuration where IK has no unique solution |

---

*Next worksheet: Worksheet 3 — Gait Patterns and Timing*
