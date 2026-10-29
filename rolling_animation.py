"""Rigid quarter-turns around a grid edge; no game rules or Ursina timers."""
from math import cos, sin, pi

from gameModel.block import Direction, Orientation


class RollingAnimation:
    def __init__(self, mesh, block, direction, duration=0.22):
        self.mesh = mesh
        self.duration = duration
        self.elapsed = 0.0
        self.cancelled = False
        self.finished = False
        self.dx, self.dz = {
            Direction.UP: (0, 1), Direction.DOWN: (0, -1),
            Direction.LEFT: (-1, 0), Direction.RIGHT: (1, 0),
        }[direction]
        width, depth = ((1, 1) if block.orientation == Orientation.SPLIT
                        else (1 + block.dc, 1 + block.dr))
        self.half_extent = (width if self.dx else depth) / 2
        x, y, z = mesh.position
        # Visible dimensions are cell dimensions minus .1. The inset pivot
        # makes the rotated box land exactly on the next grid pose, without
        # stretching it or sliding its center along a straight line.
        self.pivot = (x + self.dx*self.half_extent, y - .05,
                      z + self.dz*self.half_extent)

    def advance(self, delta):
        if self.cancelled:
            return False
        self.elapsed = min(self.duration, self.elapsed + max(0.0, delta))
        t = self.elapsed / self.duration
        t = t*t*(3 - 2*t)
        angle = t*pi/2
        along = -self.half_extent*cos(angle) + .05*sin(angle)
        height = self.half_extent*sin(angle) + .05*cos(angle)
        x, y, z = self.pivot
        self.mesh.position = (x + self.dx*along, y + height, z + self.dz*along)
        # Ursina uses y-up-left: positive Z tips towards +X, positive X to +Z.
        self.mesh.rotation = (self.dz*t*90, 0, self.dx*t*90)
        self.finished = self.elapsed >= self.duration - 1e-9
        return self.finished

    def cancel(self):
        self.cancelled = True
