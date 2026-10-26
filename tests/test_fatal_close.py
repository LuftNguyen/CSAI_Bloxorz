"""Fatal CLOSE is a terminal rule; five seconds belongs only to presentation."""
from copy import deepcopy
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Board, Tile as T
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.rules import transition, winning
from gameModel.state import State
from levels.levelLoader import _load


def fixture(fatal=True, kind=T.SOFT_SWITCH):
    b = Board(5, 8, startR=1, startC=1)
    b.setTile(1, 2, kind)
    b.setTile(1, 7, T.GOAL)
    b.addBridgeGroup('gate', [(4, 7)], True)
    b.switchEffects[(1, 2)] = (('gate', 'CLOSE'),)
    b.switchEffects[(1, 5)] = (('gate', 'OPEN'),)
    b.fatalCloseSwitches = frozenset({(1, 2)}) if fatal else frozenset()
    b.initialTiles = deepcopy(b.tiles)
    return State(b, Block(1, 1))


class FatalCloseEngineTests(unittest.TestCase):
    def test_terminal_close_is_rejected_by_problem_and_cannot_reopen(self):
        s = fixture()
        before = s.copy()
        child, valid, loss = transition(s, D.RIGHT)
        self.assertFalse(valid)
        self.assertTrue(loss)
        self.assertEqual(child.board.fatalSwitch, (1, 2))
        self.assertFalse(child.board.bridgeState['gate'])
        self.assertIsNone(Problem(s).result(s, D.RIGHT))
        self.assertEqual(s, before)
        self.assertFalse(winning(child))
        self.assertTrue(all(Problem(child).result(child, a) is None for a in D))
        child.board.applySwitch((1, 5))
        child.board.toggleBridge('gate')
        self.assertFalse(child.board.bridgeState['gate'])
        live = before.copy()
        c = GameController(live.board, live.block)
        self.assertFalse(c.executeMove(D.RIGHT))
        self.assertTrue(c.isGameOver)
        self.assertFalse(c.hasWon)
        self.assertEqual(State(c.board, c.block), child)
        self.assertFalse(c.executeMove(D.DOWN))
        c.reset()
        self.assertEqual(State(c.board, c.block), before)

    def test_ordinary_close_and_heavy_activation_are_preserved(self):
        s = fixture(fatal=False)
        child, valid, loss = transition(s, D.RIGHT)
        self.assertTrue(valid)
        self.assertFalse(loss)
        child.board.applySwitch((1, 5))
        self.assertTrue(child.board.bridgeState['gate'])
        heavy = fixture(kind=T.HEAVY_SWITCH)
        child, valid, _ = transition(heavy, D.RIGHT)
        self.assertTrue(valid)  # Lying across a heavy switch is safe.
        self.assertIsNone(child.board.fatalSwitch)
        heavy.block = Block(1, 3, 0, 1, O.LYING)
        child, valid, loss = transition(heavy, D.LEFT)
        self.assertFalse(valid)
        self.assertTrue(loss)
        self.assertEqual(child.board.fatalSwitch, (1, 2))

    def test_fatal_already_closed_and_simultaneous_open_cannot_rescue(self):
        s = fixture()
        s.board.bridgeState['gate'] = False
        s.board.setTile(4, 7, T.VOID)
        s.board.setTile(1, 3, T.SOFT_SWITCH)
        s.board.switchEffects[(1, 3)] = (('gate', 'OPEN'),)
        child, valid, loss = transition(s, D.RIGHT)
        self.assertFalse(valid)
        self.assertTrue(loss)
        self.assertFalse(child.board.bridgeState['gate'])

    def test_teleport_soft_destination_can_trigger_fatal_close(self):
        s = fixture()
        s.board.setTile(1, 2, T.NORMAL)
        s.board.setTile(1, 4, T.SPLIT_SWITCH)
        s.board.setTile(3, 1, T.SOFT_SWITCH)
        s.board.switchEffects[(3, 1)] = (('gate', 'CLOSE'),)
        s.board.fatalCloseSwitches = frozenset({(3, 1)})
        s.board.splitTargets[(1, 4)] = ((3, 1), (3, 5))
        middle = Problem(s).result(s, D.RIGHT)
        child, valid, loss = transition(middle, D.RIGHT)
        self.assertFalse(valid)
        self.assertTrue(loss)
        self.assertEqual(child.board.fatalSwitch, (3, 1))
        self.assertEqual(child.block.orientation, O.SPLIT)

    def test_equality_hash_include_configuration_and_terminal_marker(self):
        s = fixture()
        other = s.copy()
        other.board.fatalCloseSwitches = frozenset()
        self.assertNotEqual(s, other)
        self.assertEqual(len({s, other}), 2)
        other = s.copy()
        other.board.fatalSwitch = (1, 2)
        self.assertNotEqual(s, other)
        self.assertEqual(len({s, other}), 2)
        copied = s.copy()
        self.assertEqual(hash(s), hash(copied))
        self.assertEqual(s, copied)

    def test_loader_validates_optional_flag(self):
        data = dict(schema_version=2, rows=3, cols=8, start=dict(r=1,c=1),
                    grid=['XXXXXXXX','XSw.B.GX','XXXXXXXX'],
                    bridges=[dict(id='g',initial_open=True,tiles=[[1,4]])],
                    switches=[dict(position=[1,2],fatal_close=True,
                                   effects=[dict(bridge='g',mode='CLOSE')])])
        b, _ = _load(data)
        self.assertIn((1, 2), b.fatalCloseSwitches)
        for value in ['true', 1, None]:
            bad = deepcopy(data)
            bad['switches'][0]['fatal_close'] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'boolean'):
                _load(bad)
        bad = deepcopy(data)
        bad['switches'][0]['effects'][0]['mode'] = 'OPEN'
        with self.assertRaisesRegex(ValueError, 'only CLOSE'):
            _load(bad)
        del data['switches'][0]['fatal_close']
        self.assertFalse(_load(data)[0].fatalCloseSwitches)


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class FatalClosePresentationTests(unittest.TestCase):
    def make_fatal_view(self):
        from test_gui_rules import make_view
        v = make_view()
        s = fixture()
        v.gameModel = GameController(s.board, s.block)
        v.problem = Problem(s.copy())
        v.fatalMessage = SimpleNamespace(text='', enabled=False)
        v.animateFall = Mock()
        return v

    def test_five_seconds_then_loss_notice_and_reset_once(self):
        v = self.make_fatal_view()
        with patch('view.invoke', return_value=SimpleNamespace(kill=Mock())) as invoke:
            self.assertTrue(v.beginMove(D.RIGHT))
            self.assertTrue(v.gameModel.isGameOver and v.isAnimating)
            self.assertIn('5 s', v.fatalMessage.text)
            self.assertFalse(v.beginMove(D.DOWN))
            v.animateFall.assert_not_called()
            v.updateAnimations(4.9)
            self.assertIn('1 s', v.fatalMessage.text)
            invoke.assert_not_called()
            v.updateAnimations(0.1)
            self.assertIn('YOU LOSE', v.fatalMessage.text)
            self.assertEqual(invoke.call_args.kwargs['delay'], 1.0)
            self.assertEqual(invoke.call_count, 1)
            v.updateAnimations(3)
            self.assertEqual(invoke.call_count, 1)
            invoke.call_args.args[0]()
            self.assertFalse(v.gameModel.isGameOver or v.isAnimating)
            self.assertIsNone(v.gameModel.board.fatalSwitch)
            self.assertFalse(v.fatalMessage.enabled)
            self.assertEqual(v.solverMessage.text, '')

    def test_restart_and_level_change_cancel_countdown_or_old_notice(self):
        from test_gui_rules import ROOT
        from levels.levelLoader import loadLevelFromJson
        for change in (False, True):
            for notice in (False, True):
                with self.subTest(change=change, notice=notice):
                    v = self.make_fatal_view()
                    handle = SimpleNamespace(kill=Mock())
                    with patch('view.invoke', return_value=handle) as invoke:
                        v.beginMove(D.RIGHT)
                        if notice:
                            v.updateAnimations(5)
                            stale = invoke.call_args.args[0]
                        if change:
                            v.changeLevel(loadLevelFromJson(ROOT/'levels/level1.json', False))
                        else:
                            v.restartLevel()
                        snapshot = State(v.gameModel.board, v.gameModel.block).copy()
                        v.updateAnimations(20)
                        if notice:
                            stale()  # A queued callback retained despite kill must be harmless.
                            handle.kill.assert_called()
                        self.assertEqual(State(v.gameModel.board, v.gameModel.block), snapshot)
                        self.assertFalse(v.fatalMessage.enabled)
                        self.assertFalse(v.isAnimating)
