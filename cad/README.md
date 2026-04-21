# CAD Files

This directory contains the 3D CAD source files for the hexapod robot body and legs.

## Software

- **FreeCAD 0.21+** — free, open-source parametric CAD: <https://www.freecad.org>
- All parts are designed as parametric FreeCAD models (`.FCStd` format).

## File Organisation

```
cad/
├── README.md            ← this file
├── print_settings.md    ← slicer settings for each part
└── stl/                 ← exported, print-ready STL files
    └── README.md        ← list of all STL files
```

## Parametric Design

Key parameters can be changed in FreeCAD's Spreadsheet workbench:

| Parameter | Default | Description |
|---|---|---|
| `servo_width_mm` | 20.0 | Width of MG996R body |
| `servo_length_mm` | 40.3 | Length of MG996R body |
| `coxa_length_mm` | 52.0 | Coxa link length |
| `femur_length_mm` | 80.0 | Femur link length |
| `tibia_length_mm` | 120.0 | Tibia link length |
| `body_radius_mm` | 90.0 | Body plate radius |

## Opening in FreeCAD

1. Install FreeCAD 0.21 or later.
2. Open any `.FCStd` file from this directory.
3. Use the **Model** tab to see the parametric feature tree.
4. Adjust spreadsheet values and the model will update automatically.

## Exporting STL Files

1. Select the solid in the model tree.
2. File → Export → STL Mesh.
3. Set **Deviation** to 0.1 mm for good print resolution.
4. Save to `stl/` directory.

See [`print_settings.md`](print_settings.md) for recommended slicer configuration.
