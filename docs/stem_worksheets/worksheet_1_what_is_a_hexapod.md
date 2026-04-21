# Worksheet 1: What Is a Hexapod?

**Subject:** Biology + Robotics  
**Grade level:** 7–10  
**Estimated time:** 45 minutes  
**Prerequisite knowledge:** None

---

## Learning Objectives

By the end of this worksheet, you will be able to:

1. Define the word *hexapod* and give examples from biology.
2. Explain why six legs provide a stability advantage over four.
3. Describe the concept of a *support polygon* and the *stability triangle*.
4. Identify the three joints in each robot leg and match them to biological anatomy.
5. Sketch the stability triangle for tripod and wave gaits.

---

## Background: Insects — Nature's Hexapods

The word **hexapod** comes from the Greek: *hex* (six) + *pod* (foot).  
All insects are hexapods.  With over one million known species, insects are the most
successful animal group on Earth — and they all walk on six legs.

### Why do insects have six legs?

Think about a stool.  A three-legged stool never wobbles, even on uneven ground,
because three points always define a flat plane (a *triangle*).  A four-legged stool
sometimes wobbles on rough surfaces because the fourth leg may not touch the ground.

An insect walking always keeps **at least three legs on the ground** — forming a
triangle of support beneath its body.  This triangle is called the **support polygon**.
As long as the insect's centre of mass (its weight) is above the support polygon,
it is **statically stable** — it will not fall even if it freezes mid-step.

### The stability triangle

```
          Centre of mass (×)
          must be inside
          the triangle:

  Leg2 ●─────────────────● Leg1
        \        ×       /
         \              /
          \            /
           ● Leg5
```

In **tripod gait**, legs {0, 2, 4} swing while {1, 3, 5} stance, and vice versa.
The three stance legs form the support triangle.

---

## The Robot Body Plan

Our hexapod robot mimics an insect body plan with:

| Feature | Biology | Robot |
|---|---|---|
| Body (thorax) | Rigid exoskeleton | Aluminium/PETG chassis |
| Hip (coxa) | Coxa–trochanter joint | Servo, rotates horizontally |
| Thigh (femur) | Femur | Servo, rotates vertically |
| Shin (tibia) | Tibia | Servo, rotates vertically |
| Foot | Tarsus + claws | TPU rubber tip |
| Nerves | Ganglia | Raspberry Pi computer |
| Muscles | Pairs of flexors/extensors | Single servo per joint |

**Key difference:** Insect muscles come in *antagonistic pairs* (one to flex, one to extend).
A servo motor can both push and pull electronically, so one servo replaces the muscle pair.

---

## Degrees of Freedom (DOF)

Each joint that can rotate independently adds one **degree of freedom**.  
Our robot leg has **3 DOF**:

1. **Coxa** — rotates left/right (yaw)  
2. **Femur** — lifts/lowers the knee (pitch/elevation)  
3. **Tibia** — bends the knee (knee angle)

With 3 DOF per leg and 6 legs we have **18 servos total** and **18 DOF**.

**Question 1:** A dog has 4 legs, each with 3 joints.  How many DOF does a dog's
locomotion system have?  

___________________________

**Question 2:** A snake moves without any legs.  How does it achieve locomotion?  

___________________________

---

## Discussion Questions

1. Why do most robots use an even number of legs?

2. A hexapod in tripod gait always has 3 legs on the ground.
   How many legs does a hexapod in *wave gait* have on the ground at once?

3. Think about a tightrope walker.  Where does their centre of mass need to be?
   How is this similar to the support polygon concept?

4. Insects can walk on walls and ceilings.  What physical mechanism allows this?
   Could our robot walk on walls?  What would need to change?

5. Compare the speed of a centipede (many legs) to a cheetah (four legs).
   More legs does not always mean faster — why not?

---

## Activity: Draw the Support Triangle

For each gait below, shade the legs that are in **stance** (on the ground).
Draw lines connecting the stance legs to show the support triangle.
Mark the approximate centre of mass with an × inside the triangle.

**Top-view leg map:**

```
     FRONT
  Leg0   Leg1
Leg2       Leg3
  Leg4   Leg5
      BACK
```

### Tripod Gait — Phase A

Legs in stance: {1, 3, 5}

Draw your triangle:

```
     FRONT
  ___   ___
___       ___
  ___   ___
      BACK
```

### Tripod Gait — Phase B

Legs in stance: {0, 2, 4}

Draw your triangle (your own diagram below):

```
(draw here)
```

### Wave Gait — One leg swinging (Leg 0)

Legs in stance: {1, 2, 3, 4, 5}

Is the support polygon larger or smaller than in tripod gait?

___________________________

---

## Vocabulary List

| Term | Definition |
|---|---|
| Hexapod | An animal or robot with six legs |
| Support polygon | The shape formed by connecting all ground-contact points |
| Stability triangle | Support polygon when exactly three legs are on the ground |
| Centre of mass | The point where an object's weight acts; the balance point |
| Static stability | Stable even when moving slowly or stopped |
| Degree of freedom (DOF) | One independent axis of rotation or translation |
| Coxa | The hip segment (first link from the body) |
| Femur | The thigh segment (second link) |
| Tibia | The shin segment (third link, closest to foot) |
| Gait | A repeating pattern of leg movements used for locomotion |
| Tripod gait | A gait where alternating groups of 3 legs swing/stance |
| Wave gait | A gait where one leg at a time swings (most stable) |

---

## Extension Challenge

Design your own animal-inspired robot on paper.  Choose:
- Number of legs (4, 6, 8, …)
- Number of joints per leg
- A terrain it is optimised for (sand, rock, water, …)

Draw a top-down and side-view sketch.  Label every joint.  
Calculate the total number of degrees of freedom.

---

*Next worksheet: Worksheet 2 — Trigonometry and Inverse Kinematics*
