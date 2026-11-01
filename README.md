# Image to Smooth BBModel Architect

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Blockbench: 4.5+](https://img.shields.io/badge/blockbench-4.5+-orange.svg)](https://www.blockbench.net/)

Convert 2D character turnaround sheets or reference concept art into **smooth, organic, rigged Blockbench (`.bbmodel`) 3D models** without blocky voxel or staircase artifacts.

---

## 🌟 Key Features

1. **Continuous Smooth Meshes (`"type": "mesh"`, `"shading": "smooth"`)**
   - Replaces traditional cube-stacked Minecraft-style models with parametric lofted polygonal geometry (`N_THETA >= 36`).
   - Generates natural organic curvature for bodies, snouts, cheeks, curved limbs, and tapered extremities.

2. **4-Quadrant Texture Atlas Architecture**
   - Synthesizes a unified `256x256` RGBA texture atlas split cleanly into 4 quadrants:
     - **Q1 (`[0..128, 0..128]`)**: Front skin cylindrical projection and markings.
     - **Q2 (`[128..256, 0..128]`)**: Back skin projection.
     - **Q3 (`[0..128, 128..256]`)**: Dedicated limb gradients (arms/hands & legs/feet).
     - **Q4 (`[128..256, 128..256]`)**: Concentric iris/pupil eye maps and isolated feature swatches to eliminate color bleeding.

3. **Hierarchical Outliner Rigging & Animations**
   - Compliant with Blockbench `format_version: "4.5"` freeform schema.
   - Standard anatomical bone hierarchy (`root` → `body` → `head`, `eyes`, `arms`, `legs`).
   - Integrated Catmull-Rom looping keyframe animations (`idle` breathing/sway and `walk` cycles).

4. **Offline 4-View 3D Verification Engine**
   - Headless Matplotlib + NumPy 3D rendering pipeline generating `SIDE`, `FRONT`, `BACK`, and `3D PERSPECTIVE` views directly from `.bbmodel` JSON.
   - Verifies visual quality and silhouette alignment before exporting.

---

## 📁 Repository Structure

```
image-to-smooth-bbmodel/
├── SKILL.md                     # Agent skill instructions & procedural modeling workflow
├── scripts/
│   └── bbmodel_mesh_utils.py    # Reusable mesh generation & 3D preview utilities
├── tests/
│   └── test_bbmodel_mesh_utils.py # Automated test suite for mesh generation & verification
├── .gitignore
└── README.md
```

---

## 🚀 Quick Start

### Installation & Dependencies

```bash
git clone https://github.com/lindaokeefe472-eng/image-to-smooth-bbmodel.git
cd image-to-smooth-bbmodel
pip install matplotlib numpy pillow
```

### Running Tests

```bash
python -m pytest tests/test_bbmodel_mesh_utils.py
```

### Basic Usage Example

```python
from scripts.bbmodel_mesh_utils import MeshBuilder, add_lofted_tube, render_bbmodel_ortho_preview

# 1. Initialize mesh builder
mb = MeshBuilder("torso", color=1)

# 2. Define cross-section frames: (cx, cy, cz, rx, ry, rz, tilt_z, tilt_x, param)
frames = [
    (0.0, 2.0, 0.0, 4.0, 0.0, 3.5, 0.0, 0.0, 0.0),
    (0.0, 10.0, 0.0, 5.0, 0.0, 4.2, 0.0, 0.0, 0.5),
    (0.0, 18.0, 0.0, 3.8, 0.0, 3.0, 0.0, 0.0, 1.0),
]

# 3. Loft tubular body with smooth shading
add_lofted_tube(
    mb,
    frames,
    uv_func=lambda wx, wy, wz, yp, ang: (64.0, 64.0),
    cap_start=True,
    cap_end=True,
    n_seg=24,
)

mesh_element = mb.to_element()

# 4. Render offline 4-view preview from .bbmodel JSON
# render_bbmodel_ortho_preview("output.bbmodel", "preview_4view.png")
```

---

## 📄 License

[MIT License](LICENSE)
