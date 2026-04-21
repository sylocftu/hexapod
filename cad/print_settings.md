# Print Settings

Tested on Bambu Lab X1C and Prusa MK4.  All settings assume a **0.4 mm brass nozzle**.

---

## Global Slicer Settings

| Parameter | Value |
|---|---|
| Layer height | 0.20 mm |
| First layer height | 0.25 mm |
| Nozzle diameter | 0.4 mm |
| Infill pattern | Gyroid |
| Infill density | 30 % |
| Perimeters / walls | 4 |
| Top/bottom layers | 5 |
| Print speed | 60 mm/s (perimeters 45 mm/s) |
| Travel speed | 180 mm/s |
| Cooling | Max fan after layer 2 |

---

## Per-Part Settings

| Part | Material | Supports | Infill | Est. Time | Notes |
|---|---|---|---|---|---|
| `body_top.stl` | PETG | From build plate | 30 % | 4 h | Orient flat side down |
| `body_bottom.stl` | PETG | From build plate | 30 % | 3.5 h | Orient flat side down |
| `coxa_left.stl` | PETG | Yes (everywhere) | 40 % | 1 h | Mirror for right side |
| `coxa_right.stl` | PETG | Yes (everywhere) | 40 % | 1 h | Mirror of coxa_left |
| `femur.stl` | PETG | Yes (everywhere) | 40 % | 1.5 h | Print 6 copies |
| `tibia.stl` | PETG | No | 35 % | 0.75 h | Print 6 copies |
| `foot_tip.stl` | TPU 95A | No | 30 % | 0.25 h | Print 6 copies; flexible |
| `servo_horn_adapter.stl` | PETG | No | 50 % | 0.15 h | Print 18 copies |
| `camera_mount.stl` | PETG | From build plate | 30 % | 0.5 h | Front-facing |
| `sensor_bracket.stl` | PETG | No | 30 % | 0.25 h | Print 3 copies |

---

## Material Recommendations

### PETG (structural parts)
- Bed temp: 70–80 °C
- Nozzle temp: 235–245 °C
- Bed surface: PEI or glass with hairspray
- Drying: 6 h at 65 °C if filament has been stored >1 week
- Brand suggestions: eSUN PETG, Prusament PETG

### TPU 95A (foot tips)
- Bed temp: 30–40 °C
- Nozzle temp: 220–230 °C
- Print speed: **25 mm/s** (slow down significantly)
- Direct drive extruder recommended; Bowden requires filament drying
- Brand suggestions: Polymaker PolyFlex TPU95, Sainsmart TPU

---

## Support Settings

When supports are required:
- Support style: **Tree** (Bambu / Orca Slicer) or **Organic** (PrusaSlicer)
- Support Z distance: 0.25 mm
- Support interface layers: 3
- Support interface spacing: 0.2 mm
- Remove supports carefully with flush cutters

---

## Post-Processing

### Heat-Set Inserts
All M3 holes labelled `[HI]` in the part name use **M3 × 4 mm brass heat-set inserts**:
1. Heat soldering iron to 200–220 °C.
2. Place insert on hole; push gently with iron tip.
3. Sink flush or 0.1 mm below surface.
4. Let cool 60 s before assembly.

### Mating Surfaces
Lightly sand mating faces of coxa ↔ femur and femur ↔ tibia joints with 220-grit paper
for consistent rotation and reduced slop.

### Foot Tips
Press-fit the TPU foot tip onto the tibia end.  Apply a drop of CA glue inside if loose.
