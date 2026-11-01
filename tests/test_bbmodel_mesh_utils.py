import base64
import io
import json
import os
import shutil
import unittest
from PIL import Image

from scripts.bbmodel_mesh_utils import (
    UuidFactory,
    uv_clamp,
    MeshBuilder,
    add_lofted_tube,
    render_bbmodel_ortho_preview,
)


class TestBBModelMeshUtils(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_output")
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_uuid_factory_determinism(self):
        f1 = UuidFactory("test_ns")
        f2 = UuidFactory("test_ns")
        u1 = f1.next()
        u2 = f2.next()
        self.assertEqual(u1, u2)
        u3 = f1.next()
        self.assertNotEqual(u1, u3)

    def test_uv_clamp(self):
        self.assertEqual(uv_clamp(-10.0), 0.5)
        self.assertEqual(uv_clamp(300.0), 255.5)
        self.assertEqual(uv_clamp(128.456), 128.46)

    def test_mesh_builder_structure(self):
        mb = MeshBuilder("test_mesh", color=3)
        v0 = mb.add_vertex(0, 0, 0)
        v1 = mb.add_vertex(1, 0, 0)
        v2 = mb.add_vertex(1, 1, 0)
        v3 = mb.add_vertex(0, 1, 0)

        f0 = mb.add_face([v0, v1, v2, v3], {v0: (0, 0), v1: (10, 0), v2: (10, 10), v3: (0, 10)})
        elem = mb.to_element()

        self.assertEqual(elem["name"], "test_mesh")
        self.assertEqual(elem["type"], "mesh")
        self.assertEqual(elem["shading"], "smooth")
        self.assertEqual(elem["origin"], [0, 0, 0])
        self.assertEqual(elem["rotation"], [0, 0, 0])
        self.assertEqual(len(elem["vertices"]), 4)
        self.assertEqual(len(elem["faces"]), 1)
        self.assertEqual(elem["faces"][f0]["vertices"], [v0, v1, v2, v3])

    def test_add_lofted_tube(self):
        mb = MeshBuilder("tube")
        frames = [
            (0.0, 0.0, 0.0, 2.0, 0.0, 2.0, 0.0, 0.0, 0.0),
            (0.0, 5.0, 0.0, 2.0, 0.0, 2.0, 0.0, 0.0, 0.5),
            (0.0, 10.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 1.0),
        ]

        def sample_uv(wx, wy, wz, yp, ang):
            return (10.0 + yp * 20.0, 10.0 + ang * 10.0)

        add_lofted_tube(mb, frames, sample_uv, cap_start=True, cap_end=True, n_seg=8)
        elem = mb.to_element()

        # 8 segs * 3 rings + 2 pole caps = 26 vertices
        self.assertEqual(len(elem["vertices"]), 26)
        # 8 start cap triangles + 2 * 8 quads + 8 end cap triangles = 32 faces
        self.assertEqual(len(elem["faces"]), 32)

    def test_e2e_render_bbmodel_ortho_preview(self):
        # Create a simple synthetic 64x64 texture
        img = Image.new("RGBA", (64, 64), color=(100, 180, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        tex_b64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

        # Build a simple mesh
        mb = MeshBuilder("body")
        frames = [
            (0.0, 2.0, 0.0, 3.0, 0.0, 3.0, 0.0, 0.0, 0.0),
            (0.0, 15.0, 0.0, 4.0, 0.0, 4.0, 0.0, 0.0, 0.5),
            (0.0, 28.0, 0.0, 2.0, 0.0, 2.0, 0.0, 0.0, 1.0),
        ]
        add_lofted_tube(
            mb,
            frames,
            lambda wx, wy, wz, yp, ang: (32.0, 32.0),
            cap_start=True,
            cap_end=True,
            n_seg=12,
        )

        bbmodel_data = {
            "meta": {
                "format_version": "4.5",
                "model_format": "free",
                "box_uv": False,
            },
            "name": "test_model",
            "textures": [
                {
                    "name": "atlas.png",
                    "id": "0",
                    "source": tex_b64,
                }
            ],
            "elements": [mb.to_element()],
            "outliner": [
                {
                    "name": "root",
                    "origin": [0, 0, 0],
                    "children": [mb.to_element()["uuid"]],
                }
            ],
        }

        model_path = os.path.join(self.test_dir, "test_character.bbmodel")
        preview_path = os.path.join(self.test_dir, "test_preview.png")

        with open(model_path, "w", encoding="utf-8") as f:
            json.dump(bbmodel_data, f)

        # Run preview renderer
        render_bbmodel_ortho_preview(model_path, preview_path)

        self.assertTrue(os.path.exists(preview_path))
        self.assertGreater(os.path.getsize(preview_path), 1000)

        # Verify rendered image properties
        with Image.open(preview_path) as preview_img:
            self.assertEqual(preview_img.size, (2400, 750))  # 16x5 inches at 150 DPI


if __name__ == "__main__":
    unittest.main()
