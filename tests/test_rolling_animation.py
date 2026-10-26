"""Check rigid geometry, frame-rate independence and cancellation of rolls."""
import importlib.util
from itertools import product
from types import SimpleNamespace
import unittest

from gameModel.block import Block, Direction as D, Orientation as O
from rolling_animation import RollingAnimation


def pose(block):
    if block.orientation == O.SPLIT:
        return (block.c, 0, -block.r), (.9, .9, .9)
    return ((block.c + block.dc/2, 0, -(block.r + block.dr/2)),
            (.9 + block.dc, 1.9 if block.orientation == O.STANDING else .9, .9 + block.dr))


class RollingTests(unittest.TestCase):
    def test_horizontal_side_roll_rotates_and_lifts_without_stretching(self):
        block = Block(3,3,0,1,O.LYING)
        position, scale = pose(block)
        mesh = SimpleNamespace(position=position, scale=scale, rotation=(0,0,0))
        roll = RollingAnimation(mesh, block, D.DOWN)
        self.assertFalse(roll.advance(.11))
        self.assertEqual(mesh.rotation, (-45,0,0))
        self.assertEqual(mesh.scale, scale)
        self.assertGreater(mesh.position[1], .3)
        self.assertFalse(roll.finished)
        self.assertTrue(roll.advance(.11))
        self.assertEqual(mesh.scale, scale)
        self.assertEqual(mesh.rotation, (-90,0,0))

    def test_frame_rates_reach_the_same_pose_and_cancel_stops_updates(self):
        block = Block(3,3)
        meshes = []
        for delta in (1/60, .1, 1):
            position, scale = pose(block)
            mesh = SimpleNamespace(position=position, scale=scale)
            roll = RollingAnimation(mesh, block, D.RIGHT)
            while not roll.advance(delta):
                pass
            meshes.append(mesh)
        for mesh in meshes[1:]:
            for actual, expected in zip(mesh.position, meshes[0].position):
                self.assertAlmostEqual(actual, expected)
            self.assertEqual(mesh.rotation, meshes[0].rotation)
        roll.cancel()
        position = mesh.position
        self.assertFalse(roll.advance(10))
        self.assertEqual(mesh.position, position)


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class RenderedGeometryTests(unittest.TestCase):
    def test_all_rolls_land_with_exact_engine_bounds_in_ursina_coordinates(self):
        from panda3d.core import loadPrcFileData, unloadPrcFile, Vec3
        page = loadPrcFileData('roll-test', 'coordinate-system y-up-left')
        from ursina import Entity
        try:
            blocks = [Block(3,3), Block(3,3,0,1,O.LYING), Block(3,3,1,0,O.LYING),
                      Block.split(((3,3),(8,8)))]
            for block, direction in product(blocks, (D.UP,D.DOWN,D.LEFT,D.RIGHT)):
                with self.subTest(block=block, direction=direction):
                    position, scale = pose(block)
                    mesh = Entity(position=position, scale=scale, add_to_scene_entities=False)
                    try:
                        roll = RollingAnimation(mesh, block, direction)
                        roll.advance(.11)
                        for actual, expected in zip(mesh.scale, scale):
                            self.assertAlmostEqual(actual, expected)
                        # Check the actual engine transform, including its handedness.
                        roll.advance(.11)
                        vertices = [mesh.get_mat().xform_point(Vec3(x,y,z))
                                    for x,y,z in product((-.5,.5),(0,1),(-.5,.5))]
                        target, size = pose(block.resultingState(direction))
                        expected_min = (target[0]-size[0]/2, 0, target[2]-size[2]/2)
                        expected_max = (target[0]+size[0]/2, size[1], target[2]+size[2]/2)
                        for axis in range(3):
                            self.assertAlmostEqual(min(v[axis] for v in vertices), expected_min[axis], places=5)
                            self.assertAlmostEqual(max(v[axis] for v in vertices), expected_max[axis], places=5)
                    finally:
                        mesh.removeNode()
        finally:
            unloadPrcFile(page)
