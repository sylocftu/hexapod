# Worksheet 3: Gait Patterns and Timing

**Subject:** Mathematics + Robotics  
**Grade level:** 9–12  
**Estimated time:** 50 minutes  
**Prerequisite knowledge:** Worksheets 1 and 2

---

## Learning Objectives

1. Read and interpret gait phase diagrams (timing charts).
2. Calculate the **duty factor** for each gait.
3. Understand the relationship between stability and speed.
4. Modify gait parameters in the Python GaitEngine.
5. Design a custom gait and implement it.

---

## Background: What Is a Gait?

A **gait** is a repeating sequence of leg movements.  Each leg alternates between:

- **Swing phase** — foot is in the air, moving to a new position.
- **Stance phase** — foot is on the ground, pushing the body forward.

The **duty factor** (β) is the fraction of the cycle time that a leg spends in stance:

$$\beta = \frac{t_{\text{stance}}}{t_{\text{cycle}}}$$

Higher β → more time on the ground → more stable, but slower.

---

## Gait Phase Diagrams

Each row is one leg.  `█` = stance (on ground).  `░` = swing (in air).

### Tripod Gait (β ≈ 0.50)

```
Time →   0%        50%      100%
Leg 0   ████████░░░░░░░░████████
Leg 1   ░░░░░░░░████████░░░░░░░░
Leg 2   ████████░░░░░░░░████████
Leg 3   ░░░░░░░░████████░░░░░░░░
Leg 4   ████████░░░░░░░░████████
Leg 5   ░░░░░░░░████████░░░░░░░░
```

Legs 0, 2, 4 swing while 1, 3, 5 stance — then swap.

### Wave Gait (β ≈ 0.83)

```
Time →   0%  17% 33% 50% 67% 83% 100%
Leg 0   ░░░███████████████████████
Leg 2   ██░░░███████████████████
Leg 4   ████░░░█████████████████
Leg 5   ██████░░░███████████████
Leg 3   ████████░░░█████████████
Leg 1   ██████████░░░███████████
```

Only one leg swings at a time — 5 legs always on the ground.

### Ripple Gait (β ≈ 0.67)

```
Time →   0%     33%    67%   100%
Leg 0   ░░░░████████████████░░░░
Leg 3   ░░░░████████████████░░░░
Leg 2   ████░░░░████████████████
Leg 5   ████░░░░████████████████
Leg 4   ████████░░░░████████████
Leg 1   ████████░░░░████████████
```

Two legs swing at a time in overlapping groups.

---

## Exercise 3.1: Calculate Duty Factors

Using the phase diagrams above, fill in the table:

| Gait | Legs swinging at once | Swing duration (% cycle) | β (duty factor) |
|---|---|---|---|
| Tripod | _____ | _____ % | _____ |
| Wave | _____ | _____ % | _____ |
| Ripple | _____ | _____ % | _____ |

**Formula:** β = 1 − (swing duration ÷ 100 %)

---

## Exercise 3.2: Speed vs. Stability Trade-off

**Given:** cycle_time = 1.0 s, step_length = 50 mm.

Average body speed ≈ `step_length × number_of_legs_swinging / cycle_time`.

| Gait | Legs swinging | Estimated speed (mm/s) |
|---|---|---|
| Tripod | 3 | _____ |
| Wave | 1 | _____ |
| Ripple | 2 | _____ |

Why is tripod gait fastest?  Why might you choose wave gait on rough terrain?

_________________________________________________________________________

---

## Python Exercise: Modifying Step Parameters

```python
from hexapod_core.gait import GaitEngine, GaitMode, StepParams
from hexapod_core.kinematics import LegIK

ik = LegIK()

# Try different step heights and lengths
for step_h in [0.020, 0.040, 0.060]:   # metres
    params = StepParams(
        step_height=step_h,
        step_length=0.050,
        cycle_time=1.0,
        body_height=-0.10,
    )
    engine = GaitEngine(ik, params)
    engine.set_mode(GaitMode.TRIPOD)
    engine.set_velocity(vx=0.05, vy=0.0, omega=0.0)

    angles = engine.tick(dt=0.02)
    print(f"step_height={step_h*1000:.0f} mm → Leg0 angles: {[f'{a:.1f}°' for a in angles[0]]}")
```

**Record observations:**

| step_height (mm) | Leg 0 Coxa | Leg 0 Femur | Leg 0 Tibia |
|---|---|---|---|
| 20 | | | |
| 40 | | | |
| 60 | | | |

**Question:** Why does increasing step height increase femur angle range?

_________________________________________________________________________

---

## Challenge: Implement a Custom 3-1-2 Gait

Design a gait where:
- 3 legs swing first (legs 0, 2, 4)
- Then 1 leg swings (leg 1)
- Then 2 legs swing (legs 3, 5)

**Phase diagram (fill in █ stance / ░ swing):**

```
Time →    0%    30%   40%   70%  100%
Leg 0    ░░░░░ _____ _____ _____ _____
Leg 1    _____ _____ ░░░░░ _____ _____
Leg 2    ░░░░░ _____ _____ _____ _____
Leg 3    _____ _____ _____ ░░░░░ _____
Leg 4    ░░░░░ _____ _____ _____ _____
Leg 5    _____ _____ _____ ░░░░░ _____
```

**Questions:**
1. What is the duty factor for this gait?  β = _____
2. What is the minimum number of legs on the ground at any time? _____
3. Is this gait statically stable? _____

To implement this in Python, you would modify the `_assign_phases()` method
in `gait_engine.py`.  The phase values (0.0–1.0) mark where in the cycle
each leg begins its swing.

**Skeleton code:**

```python
def _assign_phases_custom_312(self) -> None:
    # Phase 0.0–0.30: Legs 0, 2, 4 swing
    # Phase 0.30–0.40: Leg 1 swings
    # Phase 0.40–0.70: Legs 3, 5 swing
    self._legs[0].phase = ___
    self._legs[1].phase = ___
    self._legs[2].phase = ___
    self._legs[3].phase = ___
    self._legs[4].phase = ___
    self._legs[5].phase = ___
```

---

## Vocabulary

| Term | Definition |
|---|---|
| Swing phase | Leg is in the air, moving to a new position |
| Stance phase | Leg is on the ground, supporting the body |
| Duty factor (β) | Fraction of cycle time a leg spends in stance |
| Cycle time | Duration of one complete gait cycle (seconds) |
| Step length | Horizontal distance foot travels during one swing |
| Step height | Maximum height foot rises during swing arc |
| Phase | Position within the gait cycle [0, 1) |
| Parabolic arc | The curved Z trajectory used during swing (smooth, efficient) |

---

*Next worksheet: Worksheet 4 — Sensors and Obstacle Avoidance*
