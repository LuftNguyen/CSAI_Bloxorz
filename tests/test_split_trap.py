"""Declared trapped teleports use the same terminal/countdown flow as fatal CLOSE."""
from copy import deepcopy
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.rules import transition
from gameModel.state import State
from levels.levelLoader import _load


def data(fatal=True):
    return dict(schema_version=2, rows=5, cols=8, start=dict(r=1,c=1),
                grid=['XXXXXXXX', 'XS..TXXX', 'XXXXXXXX', 'X.XXX.GX', 'XXXXXXXX'],
                splits=[dict(position=[1,4], targets=[[3,1],[3,5]], fatal_split=fatal)])


class SplitTrapEngineTests(unittest.TestCase):
    def test_teleport_then_loss_solver_rejects_and_controller_resets(self):
        b, block = _load(data())
        initial = State(b, block).copy()
        p = Problem(initial)
        middle = p.result(initial, D.RIGHT)
        child, valid, lost = transition(middle, D.RIGHT)
        self.assertFalse(valid)
        self.assertTrue(lost)
        self.assertEqual(child.block.orientation, O.SPLIT)
        self.assertEqual(child.block.cubes, ((3,1),(3,5)))
        self.assertEqual(child.board.fatalSwitch, (1,4))
        self.assertIsNone(p.result(middle, D.RIGHT))
        self.assertIsNone(p.result(child, D.SWITCH))
        c = GameController(b, block)
        self.assertTrue(c.executeMove(D.RIGHT))
        self.assertFalse(c.executeMove(D.RIGHT))
        self.assertTrue(c.isGameOver)
        self.assertEqual(State(c.board,c.block), child)
        c.reset()
        self.assertEqual(State(c.board,c.block), initial)
        other = initial.copy()
        other.board.fatalSplitSwitches = frozenset()
        self.assertNotEqual(initial, other)
        self.assertEqual(len({initial,other}), 2)
        plain_b, plain_block = _load(data(False))
        plain = Problem(State(plain_b,plain_block))
        self.assertIsNotNone(plain.result(plain.result(plain.initial,D.RIGHT),D.RIGHT))

    def test_loader_flag_is_boolean_and_omission_keeps_existing_behavior(self):
        for value in ('true', 1, None):
            bad = data()
            bad['splits'][0]['fatal_split'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                _load(bad)
        old = data()
        del old['splits'][0]['fatal_split']
        self.assertFalse(_load(old)[0].fatalSplitSwitches)


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class SplitTrapPresentationTests(unittest.TestCase):
    def test_two_cubes_visible_and_same_five_second_loss_flow(self):
        from test_gui_rules import make_view, finish_roll
        v = make_view()
        b, block = _load(data())
        v.gameModel = GameController(b,block)
        v.fatalMessage = SimpleNamespace(text='',enabled=False)
        with patch('view.invoke', return_value=SimpleNamespace(kill=Mock())) as invoke:
            v.beginMove(D.RIGHT)
            finish_roll(v)
            v.beginMove(D.RIGHT)
            finish_roll(v)
            self.assertEqual(v.gameModel.block.orientation, O.SPLIT)
            self.assertTrue(all(m.enabled for m in v.cubeMeshes))
            self.assertFalse(v.blockMesh.enabled)
            self.assertIn('Split trap!', v.fatalMessage.text)
            self.assertIn('5 s', v.fatalMessage.text)
            self.assertFalse(v.beginMove(D.SWITCH))
            v.updateAnimations(4.99)
            invoke.assert_not_called()
            v.updateAnimations(0.01)
            self.assertIn('YOU LOSE', v.fatalMessage.text)
            invoke.call_args.args[0]()
            self.assertFalse(v.gameModel.isGameOver)
            self.assertFalse(v.fatalMessage.enabled)
            self.assertEqual(v.gameModel.block.orientation, O.STANDING)
