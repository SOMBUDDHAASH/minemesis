"""
ModernGL Shader Program Management.
"""

from __future__ import annotations
import moderngl


BASIC_VOXEL_VERTEX_SHADER = """
#version 330 core

layout (location = 0) in vec3 in_position;
layout (location = 1) in vec2 in_texcoord;
layout (location = 2) in vec3 in_normal;
layout (location = 3) in float in_ao;

uniform mat4 u_proj;
uniform mat4 u_view;
uniform mat4 u_model;

out vec2 v_texcoord;
out vec3 v_normal;
out float v_ao;
out vec3 v_world_pos;

void main() {
    vec4 world_pos = u_model * vec4(in_position, 1.0);
    v_world_pos = world_pos.xyz;
    v_texcoord = in_texcoord;
    v_normal = mat3(u_model) * in_normal;
    v_ao = in_ao;
    gl_Position = u_proj * u_view * world_pos;
}
"""

BASIC_VOXEL_FRAGMENT_SHADER = """
#version 330 core

in vec2 v_texcoord;
in vec3 v_normal;
in float v_ao;
in vec3 v_world_pos;

uniform sampler2D u_texture;
uniform vec3 u_light_dir;
uniform vec3 u_light_color;
uniform vec3 u_ambient_color;
uniform vec3 u_fog_color;
uniform float u_fog_start;
uniform float u_fog_end;
uniform vec3 u_camera_pos;

out vec4 fragColor;

void main() {
    vec4 tex_color = texture(u_texture, v_texcoord);
    if (tex_color.a < 0.1) {
        discard;
    }

    // Directional diffuse lighting
    vec3 norm = normalize(v_normal);
    float diff = max(dot(norm, -u_light_dir), 0.0);
    vec3 diffuse = diff * u_light_color;

    // Ambient Occlusion attenuation: 0.0 (full dark) to 1.0 (no occlusion)
    float ao_factor = mix(0.45, 1.0, v_ao);

    // Composite illumination
    vec3 illumination = (u_ambient_color + diffuse) * ao_factor;
    vec3 final_rgb = tex_color.rgb * illumination;

    // Distance fog
    float dist = length(v_world_pos - u_camera_pos);
    float fog_factor = clamp((dist - u_fog_start) / (u_fog_end - u_fog_start), 0.0, 1.0);
    final_rgb = mix(final_rgb, u_fog_color, fog_factor);

    fragColor = vec4(final_rgb, tex_color.a);
}
"""


class ShaderProgram:
    """Encapsulates ModernGL Program with uniform helper methods."""

    def __init__(self, ctx: moderngl.Context, vert_src: str, frag_src: str) -> None:
        self.ctx = ctx
        self.program = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

    def set_uniform_mat4(self, name: str, value: any) -> None:
        if name in self.program:
            self.program[name].write(value.astype("f4").tobytes())

    def set_uniform_vec3(self, name: str, x: float, y: float, z: float) -> None:
        if name in self.program:
            self.program[name].value = (x, y, z)

    def set_uniform_float(self, name: str, value: float) -> None:
        if name in self.program:
            self.program[name].value = float(value)

    def set_uniform_int(self, name: str, value: int) -> None:
        if name in self.program:
            self.program[name].value = int(value)
