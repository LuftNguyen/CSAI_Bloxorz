"""A face's material coordinates must not jump when a roll lands."""
import importlib.util
import unittest

from gameModel.block import Block, Direction as D
from gameModel.board import Board
from gameModel.gameController import GameController


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class BlockSurfaceTests(unittest.TestCase):
    def setUp(self):
        from panda3d.core import loadPrcFileData
        from ursina import Entity
        from test_gui_rules import make_view
        self.page = loadPrcFileData('surface-test', 'coordinate-system y-up-left')
        self.view = make_view()
        self.view.gameModel = GameController(Board(30,30,startR=10,startC=10), Block(10,10))
        self.meshes = [Entity(add_to_scene_entities=False) for _ in range(3)]
        self.view.blockMesh, self.view.cubeMeshes = self.meshes[0], self.meshes[1:]
        for mesh in self.meshes:
            face = mesh.attach_new_node('textured-body')
            face.set_pos(0,.5,0)  # Same origin offset as the real cube model.
            rim = mesh.attach_new_node('rim')
            rim.set_pos(.5,.5,.5)
            rim.set_scale(.022,1,.022)
            mesh._visual_parts = (face, rim)
            mesh._visual_rest = tuple(p.get_transform() for p in mesh._visual_parts)
        self.view.updateBlockMesh()

    def tearDown(self):
        from panda3d.core import unloadPrcFile
        for mesh in self.meshes:
            mesh.removeNode()
        unloadPrcFile(self.page)

    def snapshot(self, mesh):
        from ursina import scene
        return [part.get_mat(scene) for part in mesh._visual_parts]

    def assert_same_faces(self, mesh, before):
        for actual, expected in zip(self.snapshot(mesh), before):
            self.assertTrue(actual.almost_equal(expected, 1e-4), (actual, expected))

    def land(self, direction, mesh):
        self.assertTrue(self.view.beginMove(direction))
        self.view._roll.advance(self.view.rollDuration)
        before = self.snapshot(mesh)
        self.view.updateAnimations(0)
        self.assertIsNone(self.view._roll)
        self.assert_same_faces(mesh, before)
        return before

    def test_successive_turns_keep_every_face_and_rim_fixed_at_landing(self):
        mesh = self.view.blockMesh
        initial = self.snapshot(mesh)
        for direction in (D.RIGHT,D.DOWN,D.UP,D.LEFT)*4:
            with self.subTest(direction=direction):
                before = self.snapshot(mesh)
                self.assertTrue(self.view.beginMove(direction))
                self.view.updateAnimations(0)
                self.assert_same_faces(mesh, before)  # No jump at the next takeoff either.
                self.view._roll.advance(self.view.rollDuration)
                endpoint = self.snapshot(mesh)
                self.view.updateAnimations(0)
                self.assert_same_faces(mesh, endpoint)
        self.view.restartLevel()
        self.assert_same_faces(mesh, initial)

    def test_switch_keeps_both_cube_faces_and_inactive_cube_in_place(self):
        self.view.gameModel.block = Block.split(((10,10),(20,20)))
        self.view.updateBlockMesh()
        first, second = self.view.cubeMeshes
        inactive = self.snapshot(second)
        landed = self.land(D.RIGHT, first)
        self.assert_same_faces(second, inactive)
        self.view.beginMove(D.SWITCH)
        self.assert_same_faces(first, landed)
        self.assert_same_faces(second, inactive)
        self.land(D.DOWN, second)
        self.assert_same_faces(first, landed)

    def test_restart_mid_roll_restores_original_face_orientation(self):
        mesh = self.view.blockMesh
        initial = self.snapshot(mesh)
        self.land(D.RIGHT, mesh)
        self.view.beginMove(D.DOWN)
        roll = self.view._roll
        self.view.updateAnimations(self.view.rollDuration/2)
        self.view.restartLevel()
        self.assert_same_faces(mesh, initial)
        self.assertFalse(roll.advance(10))
        self.assert_same_faces(mesh, initial)
