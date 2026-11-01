"""Reusable utilities for generating and verifying smooth polygonal Mesh .bbmodel files."""

import base64
import io
import json
import math
import uuid
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import numpy as np
from PIL import Image


class UuidFactory:
    """Deterministic UUID generator for reproducible .bbmodel elements and bones."""

    def __init__(self, namespace_prefix="smooth_bbmodel"):
        self.prefix = namespace_prefix
        self.counter = 1000

    def next(self):
        self.counter += 1
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.prefix}_{self.counter}"))


def uv_clamp(val, low=0.5, high=255.5):
    return round(max(low, min(high, float(val))), 2)


class MeshBuilder:
    """Builds a Blockbench 'type': 'mesh' element with smooth shading and zero origin offset."""

    def __init__(self, name, color=1, uuid_factory=None):
        self.name = name
        self.color = color
        self.uuid_factory = uuid_factory or UuidFactory()
        self.vertices = {}
        self.faces = {}
        self.v_count = 0
        self.f_count = 0

    def add_vertex(self, x, y, z):
        key = f"v{self.v_count}"
        self.v_count += 1
        self.vertices[key] = [round(float(x), 3), round(float(y), 3), round(float(z), 3)]
        return key

    def add_face(self, v_keys, uv_dict, texture=0):
        fkey = f"f{self.f_count}"
        self.f_count += 1
        self.faces[fkey] = {
            "uv": {k: [uv_clamp(u), uv_clamp(v)] for k, (u, v) in uv_dict.items()},
            "vertices": list(v_keys),
            "texture": texture,
        }
        return fkey

    def to_element(self):
        return {
            "name": self.name,
            "box_uv": False,
            "color": self.color,
            "locked": False,
            "visibility": True,
            "render_order": "default",
            "shading": "smooth",
            "origin": [0, 0, 0],
            "rotation": [0, 0, 0],
            "vertices": self.vertices,
            "faces": self.faces,
            "type": "mesh",
            "uuid": self.uuid_factory.next(),
        }


def add_lofted_tube(mb, section_frames, uv_func, cap_start=True, cap_end=True, n_seg=18):
    """Lofts a smooth tubular mesh along a sequence of 3D cross-section frames.

    Each frame in section_frames is a tuple:
    (cx, cy, cz, rx, ry, rz, tilt_z_rad, tilt_x_rad, param_val)
    """
    angs = [2.0 * math.pi * j / n_seg for j in range(n_seg)]
    rings = []
    uvs = {}
    for cx, cy, cz, rx, ry, rz, tz, tx, yp in section_frames:
        cz_cos, cz_sin = math.cos(tz), math.sin(tz)
        cx_cos, cx_sin = math.cos(tx), math.sin(tx)
        r_keys = []
        for a in angs:
            lx = rx * math.cos(a)
            ly = 0.0
            lz = rz * math.sin(a)
            x1 = lx * cz_cos - ly * cz_sin
            y1 = lx * cz_sin + ly * cz_cos
            z1 = lz
            y2 = y1 * cx_cos - z1 * cx_sin
            z2 = y1 * cx_sin + z1 * cx_cos
            wx, wy, wz = cx + x1, cy + y2, cz + z2
            vk = mb.add_vertex(wx, wy, wz)
            uvs[vk] = uv_func(wx, wy, wz, yp, a)
            r_keys.append(vk)
        rings.append(r_keys)

    if cap_start:
        cx, cy, cz, _, _, _, _, _, yp = section_frames[0]
        p0 = mb.add_vertex(cx, cy, cz)
        uvs[p0] = uv_func(cx, cy, cz, yp, 0.0)
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            v0, v1 = rings[0][j], rings[0][jn]
            mb.add_face([p0, v1, v0], {p0: uvs[p0], v1: uvs[v1], v0: uvs[v0]})

    for i in range(len(rings) - 1):
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            v00 = rings[i][j]
            v01 = rings[i][jn]
            v11 = rings[i + 1][jn]
            v10 = rings[i + 1][j]
            mb.add_face([v00, v01, v11, v10], {k: uvs[k] for k in (v00, v01, v11, v10)})

    if cap_end:
        cx, cy, cz, _, _, _, _, _, yp = section_frames[-1]
        p1 = mb.add_vertex(cx, cy, cz)
        uvs[p1] = uv_func(cx, cy, cz, yp, 0.0)
        for j in range(n_seg):
            jn = (j + 1) % n_seg
            v0, v1 = rings[-1][j], rings[-1][jn]
            mb.add_face([v0, v1, p1], {v0: uvs[v0], v1: uvs[v1], p1: uvs[p1]})


def render_bbmodel_ortho_preview(bbmodel_path, output_png_path):
    """Renders Side, Front, Back, and 3D Perspective views directly from a .bbmodel file."""
    with open(bbmodel_path, "r", encoding="utf-8") as f:
        bb = json.load(f)

    tex_src = bb["textures"][0]["source"].split(",", 1)[1]
    tex_img = Image.open(io.BytesIO(base64.b64decode(tex_src))).convert("RGBA")
    tex_arr = np.array(tex_img) / 255.0
    h_tex, w_tex, _ = tex_arr.shape

    def sample_uv_list(uv_list):
        cols = []
        for u, v in uv_list:
            iu = int(np.clip(round(u), 0, w_tex - 1))
            iv = int(np.clip(round(v), 0, h_tex - 1))
            cols.append(tex_arr[iv, iu, :3])
        return np.mean(cols, axis=0)

    faces_3d = []
    colors_3d = []
    light_dir = np.array([-0.22, 0.42, -0.88])
    light_dir /= np.linalg.norm(light_dir)

    for el in bb["elements"]:
        if el.get("type") != "mesh":
            continue
        verts = el["vertices"]
        for fdata in el["faces"].values():
            vkeys = fdata["vertices"]
            pts = [np.array(verts[k], dtype=float) for k in vkeys]
            uvs = [fdata["uv"][k] for k in vkeys]
            base_c = sample_uv_list(uvs)

            if len(pts) >= 3:
                norm = np.cross(pts[1] - pts[0], pts[2] - pts[0])
                nlen = np.linalg.norm(norm)
                norm = norm / nlen if nlen > 1e-8 else np.array([0.0, 1.0, 0.0])
            else:
                norm = np.array([0.0, 1.0, 0.0])

            center_vec = np.mean(pts, axis=0) - np.array([0.0, 16.0, 0.0])
            if np.dot(norm, center_vec) < 0:
                norm = -norm

            shade = 0.80 + 0.23 * max(0.0, np.dot(norm, light_dir))
            c = np.clip(base_c * shade, 0.0, 1.0)
            faces_3d.append([[p[0], p[2], p[1]] for p in pts])
            colors_3d.append(c)

    fig = plt.figure(figsize=(16, 5), dpi=150)
    views = [
        ("SIDE VIEW (Left Profile)", 0, 0),
        ("FRONT VIEW (North -Z)", 0, -90),
        ("BACK VIEW (South +Z)", 0, 90),
        ("3D PERSPECTIVE VIEW", 14, -64),
    ]
    for idx, (title, elev, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(1, 4, idx, projection="3d")
        ax.set_proj_type("ortho" if idx < 4 else "persp")
        coll = Poly3DCollection(faces_3d, facecolors=colors_3d, edgecolors=colors_3d, linewidths=0.2)
        ax.add_collection3d(coll)
        ax.set_xlim(-11, 11)
        ax.set_ylim(-11, 11)
        ax.set_zlim(0, 33)
        ax.set_box_aspect([22, 22, 33])
        ax.view_init(elev=elev, azim=azim)
        ax.set_axis_off()
        ax.set_title(title, fontsize=10, fontweight="bold", pad=6)

    plt.tight_layout()
    plt.savefig(output_png_path, dpi=150, facecolor="white")
    plt.close(fig)
