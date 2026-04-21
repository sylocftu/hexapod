# STL Files

Place exported STL files in this directory before slicing.

## File List

| Filename | Description | Qty | Material | Notes |
|---|---|---|---|---|
| `body_top.stl` | Top body plate — mounts Raspberry Pi and camera | 1 | PETG | Supports from build plate |
| `body_bottom.stl` | Bottom body plate — mounts PCA9685, power connectors | 1 | PETG | Supports from build plate |
| `coxa_left.stl` | Coxa (hip) link for left-side legs (0, 2, 4) | 3 | PETG | Mirror for right |
| `coxa_right.stl` | Coxa (hip) link for right-side legs (1, 3, 5) | 3 | PETG | Mirror of coxa_left |
| `femur.stl` | Femur (thigh) link — identical for all legs | 6 | PETG | Supports required |
| `tibia.stl` | Tibia (shin/lower leg) link | 6 | PETG | No supports |
| `foot_tip.stl` | Flexible foot pad — press-fits onto tibia | 6 | TPU 95A | Print slowly |
| `servo_horn_adapter.stl` | Adapter between MG996R output shaft and link | 18 | PETG | High infill (50 %) |
| `camera_mount.stl` | Camera module bracket for body front | 1 | PETG | Supports from build plate |
| `sensor_bracket.stl` | HC-SR04 bracket — attaches to body front/sides | 3 | PETG | No supports |

**Total parts:** 48 printed pieces across 10 unique designs.

## Exporting from FreeCAD

1. Open `../hexapod_leg.FCStd` (or relevant assembly file).
2. Select the solid body in the Model tree.
3. File → Export → STL Mesh; set **Deviation = 0.1 mm**.
4. Save here with the filename from the table above.

See [`../print_settings.md`](../print_settings.md) for slicer configuration.
