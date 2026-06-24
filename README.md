# TerrainPreprocessing

**Offline toolchain that turns military elevation data + OpenStreetMap into
engine-ready 3D terrain, buildings, and vegetation.**

Input: standard **DTED** elevation tiles + **OSM** vector data.
Output: meshes (FBX), draped building geometry, scattered vegetation, and tiled
satellite imagery — ready to import into a game engine or simulator.

~3,100 lines of Python, plus Blender (`bpy` / `bmesh`) for headless mesh generation.

<!--
This repo's single biggest win is a render. Add one and reference it here:
- A turntable GIF or screenshot of a generated region (BlenderFiles/dtedTest.blend already exists)
- Example: a Turkey region tile with terrain + buildings + trees
![sample](Docs/region_render.png)
-->

## Pipeline

| Stage | Script | What it does |
|---|---|---|
| **1. Elevation parse** | `Scripts/lib/dted_ops*.py` | Hand-written **DTED Level 1** parser (MIL-PRF-89020B): UHL/DSI/ACC headers, `0xAA` record sync, **sign-magnitude big-endian 16-bit** decode (a DTED quirk most parsers get wrong). |
| **2. Terrain mesh** | `Scripts/exec/generate_terrain_from_dted.py` | Cross-tile **bilinear interpolation** (loads 4 neighbouring tiles at boundaries), invalid-post inpainting, then headless Blender mesh generation. |
| **3. Geodesy** | `Scripts/lib/geo_ops.py` | WGS84 **LLA → ECEF** conversion and metric degree-length math for correct real-world scaling. |
| **4. Buildings** | `Scripts/exec/osm_building_data.py` | OSM building footprints overlaid and **draped onto the terrain**, exported as a custom binary `.buildingdata` format. |
| **5. Vegetation** | `Scripts/exec/osm_forest_data.py` | Tree scatter inside OSM forest polygons via **scanline polygon fill** with a priority-queue active-edge table (real computational geometry). |
| **6. Imagery** | `Scripts/shell_py/dxt_parser.py` | DXT/DDS satellite-imagery tile pyramid (zoom levels 11 / 13 / 16) baked to a custom `.timg` format. |
| **Validation** | `Scripts/exec/dted_test.py` | **Cross-validates** the from-scratch DTED parser against **GDAL** — the right way to prove a custom binary parser is correct. |

## Standards & tech

- **DTED Level 1** elevation format (MIL-PRF-89020B)
- **WGS84** geodesy (LLA / ECEF)
- **OpenStreetMap** vector data (via blosm)
- **Blender** `bpy` / `bmesh` headless mesh generation
- **GDAL** for parser cross-validation
- Python 3.9

## Layout

```
Scripts/
  exec/        entry points (terrain / buildings / forest / dted_test)
  lib/         DTED, geo, IO and mesh ops
  shell_py/    batch wrappers + imagery (DXT) parsing
BlenderFiles/  Blender projects (e.g. dtedTest.blend)
Resources/     sample DTED tiles + generated building data
Exports/       example FBX output
```

## Scope (honest framing)

This is a **content / asset-baking pipeline**, not a runtime terrain engine — it
*feeds* an external engine. That kind of geospatial content pipeline (DTED + OSM →
engine assets) is exactly the specialism behind digital-twin and training-simulation
products.

> Note: some duplicate/legacy parser variants and hardcoded paths remain from
> development and are being cleaned up.
