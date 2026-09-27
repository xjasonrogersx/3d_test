"""Display merged.gltf with pyrender in a pyglet window.

Drag with the left mouse button to orbit, use the wheel to zoom, and press
space to switch between textured and depth rendering.
"""

from pathlib import Path
import math

import numpy as np
import pyglet
from pyglet import gl
import pyrender
import trimesh


ASSET_PATH = Path(__file__).with_name("merged.gltf")
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700


def load_scene(asset_path: Path) -> tuple[pyrender.Scene, pyrender.PerspectiveCamera]:
	loaded = trimesh.load(asset_path, file_type="gltf", force="scene")
	if not isinstance(loaded, trimesh.Scene):
		loaded = trimesh.Scene(loaded)

	bounds = loaded.bounds
	center = (bounds[0] + bounds[1]) * 0.5
	extent = float(np.max(bounds[1] - bounds[0]))
	extent = max(extent, 0.001)

	render_scene = pyrender.Scene(
		bg_color=[0.035, 0.045, 0.06, 1.0],
		ambient_light=[1.0, 1.0, 1.0],
	)
	meshes = loaded.dump(concatenate=False)
	render_scene.add(pyrender.Mesh.from_trimesh(meshes, smooth=False))

	camera = pyrender.PerspectiveCamera(
		yfov=math.radians(45.0),
		aspectRatio=WINDOW_WIDTH / WINDOW_HEIGHT,
		znear=max(extent * 0.001, 0.001),
		zfar=extent * 100.0,
	)
	camera_node = render_scene.add(camera, name="orbit_camera")

	render_scene._orbit_center = np.asarray(center, dtype=np.float32)
	render_scene._orbit_extent = extent
	render_scene._orbit_camera_node = camera_node
	return render_scene, camera


class ModelWindow(pyglet.window.Window):
	def __init__(self, render_scene: pyrender.Scene, camera: pyrender.PerspectiveCamera):
		super().__init__(
			width=WINDOW_WIDTH,
			height=WINDOW_HEIGHT,
			caption="merged.gltf | textured",
			resizable=True,
			vsync=True,
		)
		self.render_scene = render_scene
		self.camera = camera
		self.renderer = pyrender.OffscreenRenderer(WINDOW_WIDTH, WINDOW_HEIGHT)
		self.mode = "textured"
		self.yaw = math.radians(35.0)
		self.pitch = math.radians(18.0)
		self.distance = render_scene._orbit_extent * 2.4
		self.dragging = False
		self.last_mouse = (0, 0)
		self.color_buffer = np.zeros((WINDOW_HEIGHT, WINDOW_WIDTH, 4), dtype=np.uint8)
		self.update_camera()
		pyglet.clock.schedule_interval(self.render_frame, 1.0 / 60.0)

	def update_camera(self) -> None:
		center = self.render_scene._orbit_center
		distance = self.distance
		camera_position = np.array(
			[
				center[0] + distance * math.cos(self.pitch) * math.sin(self.yaw),
				center[1] + distance * math.sin(self.pitch),
				center[2] + distance * math.cos(self.pitch) * math.cos(self.yaw),
			],
			dtype=np.float32,
		)
		forward = center - camera_position
		forward /= np.linalg.norm(forward)
		right = np.cross(forward, np.array([0.0, 1.0, 0.0], dtype=np.float32))
		right /= np.linalg.norm(right)
		up = np.cross(right, forward)
		pose = np.eye(4, dtype=np.float32)
		pose[:3, :3] = np.column_stack((right, up, -forward))
		pose[:3, 3] = camera_position
		self.render_scene.set_pose(self.render_scene._orbit_camera_node, pose)

	def render_frame(self, _delta_time: float) -> None:
		flags = pyrender.RenderFlags.RGBA
		if self.mode == "depth":
			depth = self.renderer.render(self.render_scene, flags=pyrender.RenderFlags.DEPTH_ONLY)
			far = self.render_scene._orbit_extent * 4.0
			normalized = np.clip(1.0 - depth / far, 0.0, 1.0)
			grayscale = (normalized * 255).astype(np.uint8)
			self.color_buffer[:, :, :3] = grayscale[:, :, None]
			self.color_buffer[:, :, 3] = 255
		else:
			self.color_buffer, _ = self.renderer.render(self.render_scene, flags=flags)
			self.color_buffer = self.color_buffer.copy()
		self.invalid = True

	def on_draw(self) -> None:
		self.clear()
		image = pyglet.image.ImageData(
			self.width,
			self.height,
			"RGBA",
			self.color_buffer.tobytes(),
			pitch=-self.width * 4,
		)
		image.blit(0, 0, width=self.width, height=self.height)

	def on_resize(self, width: int, height: int) -> None:
		self.camera.aspectRatio = width / max(height, 1)
		self.renderer.delete()
		self.renderer = pyrender.OffscreenRenderer(width, height)
		self.color_buffer = np.zeros((height, width, 4), dtype=np.uint8)

	def on_key_press(self, symbol: int, _modifiers: int) -> None:
		if symbol == pyglet.window.key.SPACE:
			self.mode = "depth" if self.mode == "textured" else "textured"
			self.set_caption(f"merged.gltf | {self.mode}")

	def on_mouse_press(self, x: int, y: int, button: int, _modifiers: int) -> None:
		if button == pyglet.window.mouse.LEFT:
			self.dragging = True
			self.last_mouse = (x, y)

	def on_mouse_release(self, _x: int, _y: int, button: int, _modifiers: int) -> None:
		if button == pyglet.window.mouse.LEFT:
			self.dragging = False

	def on_mouse_drag(self, x: int, y: int, dx: int, dy: int, _buttons: int, _modifiers: int) -> None:
		if self.dragging:
			self.yaw -= dx * 0.01
			self.pitch = np.clip(self.pitch + dy * 0.01, -1.45, 1.45)
			self.update_camera()

	def on_mouse_scroll(self, _x: int, _y: int, _scroll_x: int, scroll_y: int) -> None:
		self.distance *= 0.88 ** scroll_y
		extent = self.render_scene._orbit_extent
		self.distance = float(np.clip(self.distance, extent * 0.25, extent * 20.0))
		self.update_camera()

	def on_close(self) -> None:
		self.renderer.delete()
		super().on_close()


def main() -> None:
	render_scene, camera = load_scene(ASSET_PATH)
	ModelWindow(render_scene, camera)
	pyglet.app.run()


if __name__ == "__main__":
	main()
