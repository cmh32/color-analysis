import math

import numpy as np

from color_analysis.cv.types import Landmarks


def synthetic_mesh_points(
    width: int = 640,
    height: int = 480,
    overrides: dict[int, tuple[int, int]] | None = None,
) -> tuple[tuple[int, int], ...]:
    center = (width // 2, height // 2)
    points = [center for _ in range(478)]
    x_scale = width / 640.0
    y_scale = height / 480.0
    points_map = {
        10: (320, 110),
        21: (260, 125),
        33: (220, 250),
        50: (300, 300),
        54: (220, 170),
        63: (250, 205),
        66: (295, 194),
        67: (280, 125),
        70: (230, 215),
        93: (200, 220),
        101: (275, 340),
        103: (245, 140),
        105: (275, 198),
        107: (310, 192),
        109: (310, 115),
        117: (235, 350),
        118: (245, 360),
        123: (225, 330),
        127: (195, 150),
        129: (260, 230),
        132: (220, 300),
        133: (280, 250),
        144: (245, 236),
        145: (255, 240),
        147: (210, 335),
        152: (320, 390),
        153: (265, 246),
        154: (265, 254),
        155: (255, 260),
        157: (265, 234),
        158: (255, 230),
        159: (245, 230),
        160: (235, 232),
        161: (225, 236),
        162: (210, 130),
        163: (235, 234),
        172: (228, 318),
        173: (275, 240),
        187: (290, 315),
        192: (225, 300),
        203: (300, 240),
        205: (320, 275),
        206: (285, 236),
        207: (305, 290),
        213: (250, 285),
        226: (240, 225),
        234: (180, 180),
        246: (215, 242),
        249: (385, 240),
        251: (430, 150),
        263: (420, 250),
        280: (340, 300),
        284: (420, 170),
        293: (390, 205),
        296: (345, 194),
        297: (360, 125),
        300: (410, 215),
        323: (440, 220),
        330: (365, 340),
        332: (395, 140),
        334: (365, 198),
        336: (330, 192),
        338: (330, 115),
        346: (405, 350),
        347: (395, 360),
        352: (415, 330),
        356: (430, 280),
        358: (380, 230),
        361: (420, 300),
        362: (360, 250),
        373: (395, 236),
        374: (385, 240),
        380: (375, 246),
        381: (375, 254),
        382: (385, 260),
        384: (375, 234),
        385: (385, 230),
        386: (395, 230),
        387: (405, 232),
        388: (415, 236),
        389: (445, 190),
        390: (405, 234),
        398: (365, 240),
        423: (340, 240),
        425: (320, 275),
        454: (460, 180),
        466: (425, 242),
        468: (250, 250),
        469: (246, 246),
        470: (254, 246),
        471: (254, 254),
        472: (246, 254),
        473: (390, 250),
        474: (386, 246),
        475: (394, 246),
        476: (394, 254),
        477: (386, 254),
    }
    for index, point in points_map.items():
        points[index] = (int(round(point[0] * x_scale)), int(round(point[1] * y_scale)))
    if overrides:
        for index, point in overrides.items():
            points[index] = point
    return tuple(points)


def synthetic_landmarks(
    photo_id: str = "photo",
    width: int = 640,
    height: int = 480,
    yaw: float = 0.0,
    pitch: float = 0.0,
    roll: float = 0.0,
    overrides: dict[int, tuple[int, int]] | None = None,
) -> Landmarks:
    mesh_points = synthetic_mesh_points(width=width, height=height, overrides=overrides)
    face_points = mesh_points[:468]
    xs = [point[0] for point in face_points]
    ys = [point[1] for point in face_points]
    return Landmarks(
        photo_id=photo_id,
        face_bbox=(min(xs), min(ys), max(xs) + 1, max(ys) + 1),
        left_eye_center=mesh_points[468],
        right_eye_center=mesh_points[473],
        mesh_points=mesh_points,
        pose_yaw_degrees=yaw,
        pose_pitch_degrees=pitch,
        pose_roll_degrees=roll,
    )


def rotation_matrix(yaw: float, pitch: float, roll: float) -> np.ndarray:
    yaw_r = math.radians(yaw)
    pitch_r = math.radians(pitch)
    roll_r = math.radians(roll)

    rx = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, math.cos(pitch_r), -math.sin(pitch_r)],
            [0.0, math.sin(pitch_r), math.cos(pitch_r)],
        ],
        dtype=np.float64,
    )
    ry = np.array(
        [
            [math.cos(yaw_r), 0.0, math.sin(yaw_r)],
            [0.0, 1.0, 0.0],
            [-math.sin(yaw_r), 0.0, math.cos(yaw_r)],
        ],
        dtype=np.float64,
    )
    rz = np.array(
        [
            [math.cos(roll_r), -math.sin(roll_r), 0.0],
            [math.sin(roll_r), math.cos(roll_r), 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float64,
    )
    matrix = np.eye(4, dtype=np.float64)
    matrix[:3, :3] = rz @ ry @ rx
    return matrix


def normalized_mesh_points(
    width: int = 640,
    height: int = 480,
    overrides: dict[int, tuple[int, int]] | None = None,
) -> list[object]:
    mesh_points = synthetic_mesh_points(width=width, height=height, overrides=overrides)

    class _Point:
        def __init__(self, x: float, y: float) -> None:
            self.x = x
            self.y = y

    return [_Point(x / max(1, width - 1), y / max(1, height - 1)) for x, y in mesh_points]
