# Assembly Guide

**Estimated time:** 6–8 hours for first build  
**Skill level:** Beginner to intermediate

---

## ⚠️ Safety First

Before you begin, read every item below.

- **LiPo batteries** store large amounts of energy and can cause fires if punctured,
  short-circuited, or over-discharged.  Never leave a charging LiPo unattended.
- Install a **10 A inline fuse** in the positive battery lead.
- Keep a **LiPo-safe charging bag** on hand.
- Disconnect the battery before working on wiring.
- Allow freshly printed PETG parts to cool for 30 minutes before handling.
- Use eye protection when using the soldering iron for heat-set inserts.

---

## Tools Needed

| Tool | Notes |
|---|---|
| Soldering iron (adjustable temp) | Set to 200–220 °C for heat-set inserts |
| M3 hex key / Allen wrench | 2.5 mm for M3 bolts |
| M2 Phillips screwdriver | For servo horn screws |
| Flush cutters / side cutters | Removing supports, trimming wire |
| Digital multimeter | Voltage / continuity checks |
| Zip ties × 20 | Cable management |
| Helping hands / PCB holder | For soldering |
| Breadboard / jumper wires | For initial testing before final assembly |

---

## Step 1: Print All Parts

1. Download and slice all STL files from `cad/stl/`.
2. Follow the settings in `cad/print_settings.md`.
3. Allow all parts to cool completely on the build plate.
4. Remove supports carefully with flush cutters.
5. Lightly sand mating surfaces of coxa, femur, and tibia with 220-grit sandpaper.

**Quality check:** All servo cavities should accept an MG996R without forcing.
Servo mounting ears should align with screw holes.

---

## Step 2: Install Heat-Set Inserts

Every M3 hole in the structural parts requires a **brass M3 × 4 mm heat-set insert**.

1. Set the soldering iron to 210 °C.
2. Place an insert on the mouth of the hole, flat end first.
3. Press gently and evenly with the iron tip until the insert is flush or 0.1 mm below surface.
4. Remove iron; hold part still for 60 seconds while the plastic re-solidifies.
5. Repeat for all holes:
   - **body_top.stl**: 8 inserts (Pi mount, camera mount)
   - **body_bottom.stl**: 12 inserts (leg mounts, PCA9685)
   - **coxa × 6**: 4 inserts each (servo and link mount)
   - **femur × 6**: 2 inserts each (tibia link mount)

---

## Step 3: Assemble One Leg (Coxa → Femur → Tibia)

Repeat for all 6 legs before attaching to body.

```
Body attachment
     │
  ┌──┴──┐  Coxa servo (horizontal rotation)
  │Coxa │─── M3×8 bolts
  └──┬──┘
     │  52 mm
  ┌──┴──┐  Femur servo (vertical rotation, elevation)
  │Femur│─── M3×8 bolts
  └──┬──┘
     │  80 mm
  ┌──┴──┐  Tibia servo (knee bend)
  │Tibia│
  └──┬──┘
     │  120 mm
  [Foot tip — TPU press-fit]
```

### Leg assembly steps:

1. Insert the **coxa servo** into the coxa cavity; secure with 4 × M2 × 6 screws.
2. Attach the **servo horn adapter** to the servo output shaft; tighten the central M2 screw.
3. Connect the coxa to the femur using M3 × 8 bolts through the servo horn adapter.
4. Repeat for the femur servo → tibia connection.
5. Press the **TPU foot tip** onto the tibia end; apply CA glue if loose.

**Tip:** Route servo cables through the internal channels before bolting links together.

---

## Step 4: Repeat for All 6 Legs

Assemble legs 0–5 following the same procedure.  
Label each servo cable with a small tag noting the leg number and joint (e.g. "L0-Coxa").

---

## Step 5: Mount Servos into Segments

Verify each servo horn is attached at **90° (neutral position)** before assembly.
This can be checked by connecting a servo tester or powering up the Pi briefly.

---

## Step 6: Attach Legs to Body Bottom

1. Place `body_bottom.stl` on your work surface.
2. Align leg 0 (Front-Left) attachment point.  Leg angles from body centre:
   - Leg 0: 45°, Leg 1: -45°, Leg 2: 90°, Leg 3: -90°, Leg 4: 135°, Leg 5: -135°
3. Secure each coxa to the body bottom with 4 × M3 × 12 bolts.
4. Route all 6 coxa servo cables up through the body access holes.

---

## Step 7: Mount PCA9685 and Raspberry Pi

1. Mount the **PCA9685** to the body bottom using M3 × 8 standoffs (4 corners).
2. Mount the **Raspberry Pi 4** to `body_top.stl` using M3 × 8 standoffs.
3. Attach the top plate to the bottom plate using M3 × 16 bolts (sides).

---

## Step 8: Wire Power

```
[LiPo 7.4V] ──[10A Fuse]──┬──[BEC 6V 10A]──[Servo Power Bus]
                           └──[BEC 5V 5A]───[Pi + Logic Power]
```

1. Solder XT60 connector to LiPo leads (red to +, black to −).
2. Solder the fuse inline with the positive lead.
3. Connect the BEC 6 V input to the power bus.
4. Connect the BEC 5 V input to the power bus.
5. Connect the BEC 5 V output to the Raspberry Pi USB-C port via appropriate cable.
6. Connect BEC 6 V V+ and GND to the PCA9685 power terminal block.

---

## Step 9: Wire I²C Bus

| Pi GPIO | Pin | → | Device |
|---|---|---|---|
| SDA (GPIO 2) | 3 | → | PCA9685 SDA, MPU-6050 SDA |
| SCL (GPIO 3) | 5 | → | PCA9685 SCL, MPU-6050 SCL |
| 3.3 V | 1 | → | PCA9685 VCC, MPU-6050 VCC |
| GND | 6 | → | PCA9685 GND, MPU-6050 GND |

Use short (10 cm) Dupont wires.  Keep I²C wires away from servo power leads.

---

## Step 10: Wire All 18 Servos to PCA9685

| Leg | Joint | PCA9685 Channel |
|---|---|---|
| 0 (Front-L) | Coxa | 0 |
| 0 (Front-L) | Femur | 1 |
| 0 (Front-L) | Tibia | 2 |
| 1 (Front-R) | Coxa | 3 |
| 1 (Front-R) | Femur | 4 |
| 1 (Front-R) | Tibia | 5 |
| 2 (Mid-L) | Coxa | 6 |
| 2 (Mid-L) | Femur | 7 |
| 2 (Mid-L) | Tibia | 8 |
| 3 (Mid-R) | Coxa | 9 |
| 3 (Mid-R) | Femur | 10 |
| 3 (Mid-R) | Tibia | 11 |
| 4 (Rear-L) | Coxa | 12 |
| 4 (Rear-L) | Femur | 13 |
| 4 (Rear-L) | Tibia | 14 |
| 5 (Rear-R) | Coxa | 15 |
| 5 (Rear-R) | Femur | 16 |
| 5 (Rear-R) | Tibia | 17 |

Use JST-XH connectors for removable servo connections.

---

## Step 11: Mount Sensors

### HC-SR04 Ultrasonic Sensors

1. Press-fit or hot-glue each sensor into its bracket (`sensor_bracket.stl`).
2. Mount the **center** bracket at the front of the body, facing forward.
3. Mount **left** and **right** brackets at 45° angles.
4. Wire each sensor per the pinout in `hardware/wiring_notes.md`.
5. Route ECHO signals through level shifters before connecting to Pi GPIO.

### MPU-6050 IMU

Mount the IMU flat on the body bottom (level surface) for accurate readings.
Ensure X axis points forward and Z axis points up.

---

## Step 12: First Power-On Checklist

Before connecting the battery:

- [ ] All solder joints inspected — no bridges or cold joints
- [ ] Fuse installed in positive lead
- [ ] BEC output voltages measured:  5V BEC = 5.0–5.2 V, 6V BEC = 5.9–6.1 V
- [ ] No exposed wire ends that could short
- [ ] I²C wiring double-checked

First power-on sequence:

1. Connect battery → wait 2 seconds.
2. All 18 servos should move to neutral (90°) if firmware is running.
3. SSH into Raspberry Pi: `ssh pi@hexapod.local`
4. Check I²C devices: `i2cdetect -y 1`  (should show 0x40 and 0x68)
5. Run: `cd hexapod && python -m pytest software/tests/ -v`

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Servo twitching or jitter | Noisy power supply | Add 100 µF capacitor across servo power bus |
| I²C not detected | Wiring error or I²C not enabled | Check wiring; run `raspi-config` → I2C |
| Leg moves wrong direction | Servo mounted inverted or wrong channel | Swap cable or set trim offset |
| Robot tips over | Body height too high or CG off-centre | Lower body height; redistribute weight |
| Hot servos | Legs hitting mechanical limits | Adjust IK offset or link lengths |
| Wi-Fi disconnects | Power draw too high | Ensure 5V BEC is rated ≥ 5 A |

See `docs/software_architecture.md` for API and software debugging tips.
