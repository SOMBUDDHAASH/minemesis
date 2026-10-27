"""
First-Person 3D Camera and Matrix Mathematics.
"""

from __future__ import annotations
import math
import numpy as np


class Camera3D:
    """3D Camera providing view and projection matrices."""

    def __init__(
        self,
        fov: float = 70.0,
        aspect: float = 16.0 / 9.0,
        near: float = 0.1,
        far: float = 1000.0,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
    ) -> None:
        self.fov = fov
        self.aspect = aspect
        self.near = near
        self.far = far

        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

        self.yaw: float = 0.0     # Degrees (0 = North/+Z, 90 = East/+X)
        self.pitch: float = 0.0   # Degrees (-89 to +89)

        self._proj_matrix: np.ndarray = np.eye(4, dtype=np.float32)
        self._view_matrix: np.ndarray = np.eye(4, dtype=np.float32)
        self.update_projection(aspect)

    def update_projection(self, aspect: float) -> None:
        self.aspect = aspect
        f = 1.0 / math.tan(math.radians(self.fov) / 2.0)
        m = np.zeros((4, 4), dtype=np.float32)
        m[0, 0] = f / aspect
        m[1, 1] = f
        m[2, 2] = (self.far + self.near) / (self.near - self.far)
        m[2, 3] = (2.0 * self.far * self.near) / (self.near - self.far)
        m[3, 2] = -1.0
        self._proj_matrix = m

    def get_forward_vector(self) -> Tuple[float, float, float]:
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)
        dx = -math.sin(yaw_rad) * math.cos(pitch_rad)
        dy = math.sin(pitch_rad)
        dz = math.cos(yaw_rad) * math.cos(pitch_rad)
        length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if length > 0.0001:
            return dx / length, dy / length, dz / length
        return 0.0, 0.0, 1.0

    def get_view_matrix(self) -> np.ndarray:
        # Build LookAt view matrix
        px, py, pz = self.x, self.y, self.z
        fx, fy, fz = self.get_forward_vector()

        # Target point
        tx, ty, tz = px + fx, py + fy, pz + fz

        # Camera axes
        f = np.array([fx, fy, fz], dtype=np.float32)
        f = f / np.linalg.norm(f)

        up = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        s = np.cross(f, up)
        norm_s = np.linalg.norm(s)
        if norm_s > 0.0001:
            s = s / norm_s
        else:
            s = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        u = np.cross(s, f)

        view = np.identity(4, dtype=np.float32)
        view[0, 0:3] = s
        view[1, 0:3] = u
        view[2, 0:3] = -f

        view[0, 3] = -np.dot(s, np.array([px, py, pz]))
        view[1, 3] = -np.dot(u, np.array([px, py, pz]))
        view[2, 3] = np.dot(f, np.array([px, py, pz]))

        self._view_matrix = view
        return self._view_matrix

    @property
    def projection_matrix(self) -> np.ndarray:
        return self._proj_matrix

    def world_to_screen(
        self,
        wx: float, wy: float, wz: float,
        screen_w: int, screen_h: int,
    ) -> Optional[Tuple[float, float, float]]:
        """
        Projects 3D world coordinate to 2D screen coordinate (x_pixel, y_pixel, depth_distance).
        Returns None if point is behind the camera or outside the viewing frustum.
        """
        pos_world = np.array([wx, wy, wz, 1.0], dtype=np.float32)
        view = self.get_view_matrix()
        proj = self.projection_matrix

        pos_view = np.matmul(view, pos_world)
        if pos_view[2] >= -0.1:  # Behind camera
            return None

        pos_clip = np.matmul(proj, pos_view)
        w = float(pos_clip[3])
        if w <= 0.001:
            return None

        ndc_x = float(pos_clip[0] / w)
        ndc_y = float(pos_clip[1] / w)

        # Frustum margin check
        if abs(ndc_x) > 1.25 or abs(ndc_y) > 1.25:
            return None

        screen_x = (ndc_x + 1.0) * 0.5 * screen_w
        screen_y = (1.0 - ndc_y) * 0.5 * screen_h
        dist = math.sqrt((wx - self.x) ** 2 + (wy - self.y) ** 2 + (wz - self.z) ** 2)

        return screen_x, screen_y, dist
