"""Convert drag velocity from the rendered screen axes to VRM spring axes."""
import math
import numpy as np


def drag_to_vrm(screen_velocity, flip, scale, yaw=0., roll=0., pitch=0.):
    """The spring solver uses raw VRM coordinates; rendering uses flip and pose."""
    y, z, x = map(math.radians, (yaw, roll, pitch))
    ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0],
                   [-math.sin(y), 0, math.cos(y)]])
    rz = np.array([[math.cos(z), -math.sin(z), 0],
                   [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)],
                   [0, math.sin(x), math.cos(x)]])
    scene = rz @ ry @ rx
    return np.asarray(flip).T @ scene.T @ np.asarray(screen_velocity, float) / max(.001, scale)
