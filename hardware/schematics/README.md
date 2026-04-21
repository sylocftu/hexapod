# Hardware Schematics

This directory contains KiCad schematic source files for the hexapod electrical system.

## Expected Files

Place the following KiCad project files here after designing the schematics:

| File | Description |
|---|---|
| `hexapod_power.kicad_sch` | LiPo → BEC → power distribution schematic |
| `hexapod_controller.kicad_sch` | Raspberry Pi + PCA9685 + MPU-6050 connections |
| `hexapod_sensors.kicad_sch` | HC-SR04 level-shifter wiring |
| `hexapod.kicad_pro` | KiCad project file |

## Software Requirements

- **KiCad 7.0+** — free, cross-platform EDA tool: <https://www.kicad.org>

## Generating PDFs

1. Open the `.kicad_sch` file in KiCad Schematic Editor.
2. File → Plot → PDF.
3. Save to this directory alongside the source files.

## Contributing Schematics

If you improve or correct the schematics:
1. Export as both `.kicad_sch` (source) and `.pdf` (readable without KiCad).
2. Update `../wiring_notes.md` if any pin assignments change.
3. Open a Pull Request with both files.

See [`../wiring_notes.md`](../wiring_notes.md) for the authoritative wiring reference.
