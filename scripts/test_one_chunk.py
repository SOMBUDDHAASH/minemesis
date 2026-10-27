"""
Standalone single-chunk rendering test.
Tests Camera3D with transpose, front_face, and renders 1 single chunk.
"""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import moderngl
import numpy as np
from PIL import Image

from engine.render.camera import Camera3D
from engine.render.shader import ShaderProgram, BASIC_VOXEL_VERTEX_SHADER, BASIC_VOXEL_FRAGMENT_SHADER
from engine.render.texture import TextureAtlas
from engine.world.block_registry import registry
from engine.world.chunk import Chunk
from engine.world.mesher import ChunkMesher


def test_chunk_render():
    print("[*] Initializing Standalone ModernGL Context...")
    ctx = moderngl.create_context(standalone=True)
    width, height = 1280, 720

    # Create FBO
    color_tex = ctx.texture((width, height), 4)
    depth_rb = ctx.depth_renderbuffer((width, height))
    fbo = ctx.framebuffer(color_attachments=[color_tex], depth_attachment=depth_rb)
    fbo.use()

    atlas = TextureAtlas(ctx)
    shader = ShaderProgram(ctx, BASIC_VOXEL_VERTEX_SHADER, BASIC_VOXEL_FRAGMENT_SHADER)

    # Create 1 test chunk with flat terrain (grass top, dirt below, bedrock at bottom)
    chunk = Chunk(0, 0)
    for z in range(16):
        for x in range(16):
            chunk.set_block(x, 0, z, 1)  # Bedrock
            for y in range(1, 10):
                chunk.set_block(x, y, z, 18) # Dirt
            chunk.set_block(x, 10, z, 19)    # Grass turf

    mesher = ChunkMesher(ctx, atlas, shader.program)
    mesher.build_mesh(chunk)

    print(f"[*] Chunk 0,0 Mesh Built:")
    print(f"    Opaque Mesh: {chunk.opaque_mesh}")
    if chunk.opaque_mesh:
        vao, vcount = chunk.opaque_mesh
        print(f"    Vertices: {vcount} ({vcount // 3} triangles)")

    # Camera: Place at (8.0, 16.0, -8.0), looking towards the chunk center (8.0, 10.0, 8.0)
    cam = Camera3D(fov=70.0, aspect=width / float(height), near=0.1, far=500.0, x=8.0, y=16.0, z=-8.0)
    # Look slightly down (+Pitch) and forward (+Z, yaw=0)
    cam.yaw = 0.0
    cam.pitch = -25.0

    # Clear screen to sky blue
    ctx.clear(0.48, 0.72, 0.98, 1.0)
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.depth_func = "<="
    # Disable cull face for now to test if geometry is visible
    ctx.disable(moderngl.CULL_FACE)

    atlas.bind(unit=0)
    shader.set_uniform_int("u_texture", 0)

    # Set uniforms with transpose (.T)
    proj = cam.projection_matrix
    view = cam.get_view_matrix()
    model = np.identity(4, dtype=np.float32)

    shader.program["u_proj"].write(np.ascontiguousarray(proj.T, dtype=np.float32).tobytes())
    shader.program["u_view"].write(np.ascontiguousarray(view.T, dtype=np.float32).tobytes())
    shader.program["u_model"].write(np.ascontiguousarray(model.T, dtype=np.float32).tobytes())

    shader.set_uniform_vec3("u_light_dir", 0.4, -0.8, 0.4)
    shader.set_uniform_vec3("u_light_color", 1.0, 0.96, 0.88)
    shader.set_uniform_vec3("u_ambient_color", 0.4, 0.4, 0.4)
    shader.set_uniform_vec3("u_fog_color", 0.48, 0.72, 0.98)
    shader.set_uniform_float("u_fog_start", 50.0)
    shader.set_uniform_float("u_fog_end", 200.0)
    shader.set_uniform_vec3("u_camera_pos", cam.x, cam.y, cam.z)

    # Render chunk
    if chunk.opaque_mesh:
        vao, vcount = chunk.opaque_mesh
        vao.render(moderngl.TRIANGLES, vertices=vcount)
        print(f"[+] Rendered chunk with {vcount} vertices!")

    # Read back image
    raw = fbo.read(components=3)
    img = Image.frombytes("RGB", (width, height), raw)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    Path("reports/screens").mkdir(parents=True, exist_ok=True)
    img.save("reports/screens/test_one_chunk.png")
    print(f"[+] Saved screenshot to reports/screens/test_one_chunk.png")

    colors = img.getcolors(1000000)
    print(f"[*] Total unique colors in rendered image: {len(colors)}")
    top_cols = sorted(colors, key=lambda x: x[0], reverse=True)[:5]
    print(f"[*] Top 5 colors: {top_cols}")


if __name__ == "__main__":
    test_chunk_render()
