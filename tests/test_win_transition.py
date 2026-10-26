"""Goal fall, one-second blackout and cancellation are presentation only."""
import importlib.util
import unittest
from unittest.mock import Mock

from gameModel.block import Direction as D
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class WinTransitionTests(unittest.TestCase):
    def test_manual_and_replay_wait_for_final_setter_then_full_black_second(self):
        from test_gui_rules import make_view, mesh, finish_movement, finish_roll
        for replay in (False, True):
            with self.subTest(replay=replay):
                v = make_view()
                v.beginMove(D.RIGHT)
                finish_roll(v)
                visible, far, hidden = mesh(), mesh(), mesh(False)
                visible.position = (4,-0.1,-1)
                far.position = (1,-0.1,-1)
                v.tileEntities = [visible, far, hidden]
                v.isSolving = replay
                v.loadNextLevel = Mock()
                v.beginMove(D.RIGHT)
                finish_roll(v)
                state = State(v.gameModel.board, v.gameModel.block).copy()
                self.assertTrue(v.isAnimating)
                self.assertFalse(v.isSolving or v._replayReady)
                self.assertTrue(visible.enabled)
                self.assertFalse(hidden.enabled)
                self.assertFalse(v.beginMove(D.LEFT))
                group = v._movement
                for h in group.handles:
                    h.finished = True
                    h.func_finished_statuses = [False]
                v.finishWinFall()  # A nominal timer/manual call cannot fake completion.
                v.updateAnimations(2)
                self.assertEqual(v._winPhase, 'fall')
                self.assertFalse(v.winBlackout.enabled)
                for h in group.handles:
                    h.func_finished_statuses = [True]
                v.updateAnimations(0)
                self.assertEqual(v._winPhase, 'collapse')
                self.assertFalse(v.winBlackout.enabled)
                self.assertTrue(visible.enabled and far.enabled)
                self.assertEqual(visible.animate_y.call_args.kwargs['delay'], 0)
                self.assertEqual(far.animate_y.call_args.kwargs['delay'], 0.32)
                collapse = v._movement
                for h in collapse.handles:
                    h.finished = True
                    h.func_finished_statuses = [True]
                collapse.handles[-1].func_finished_statuses = [False]
                v.updateAnimations(2)
                self.assertEqual(v._winPhase, 'collapse')
                self.assertFalse(v.winBlackout.enabled)
                finish_movement(v)
                self.assertEqual(v._winPhase, 'blackout')
                self.assertFalse(v.blockMesh.enabled)
                self.assertTrue(v.winBlackout.enabled)
                v.updateAnimations(0.99)
                v.loadNextLevel.assert_not_called()
                v.updateAnimations(0.01)
                v.loadNextLevel.assert_called_once()
                v.updateAnimations(5)
                v.loadNextLevel.assert_called_once()
                self.assertEqual(State(v.gameModel.board, v.gameModel.block), state)

    def test_restart_or_change_during_fall_or_blackout_cancels_old_callbacks(self):
        from test_gui_rules import ROOT, make_view, finish_movement, mesh, finish_roll
        for change in (False, True):
            for phase in ('fall', 'collapse', 'blackout'):
                with self.subTest(change=change, phase=phase):
                    v = make_view()
                    v.beginMove(D.RIGHT)
                    finish_roll(v)
                    tile = mesh()
                    original_position, original_scale = tile.position, tile.scale
                    v.tileEntities = [tile]
                    v.beginMove(D.RIGHT)
                    finish_roll(v)
                    if phase != 'fall':
                        finish_movement(v)
                    group = v._movement
                    stale = group.callback
                    if phase == 'blackout':
                        finish_movement(v)
                    if phase != 'fall':
                        tile.position, tile.scale = (1,-5,-1), (0.05,0.05,0.05)
                    if change:
                        v.changeLevel(loadLevelFromJson(ROOT/'levels/level2.json', False))
                    else:
                        v.restartLevel()
                    snapshot = State(v.gameModel.board, v.gameModel.block).copy()
                    stale()
                    group.poll()
                    v.updateAnimations(30)
                    self.assertEqual(State(v.gameModel.board, v.gameModel.block), snapshot)
                    self.assertFalse(v.winBlackout.enabled)
                    self.assertIsNone(v._winPhase)
                    self.assertTrue(v.blockMesh.enabled)
                    self.assertTrue(tile.enabled)
                    self.assertEqual(tile.position, original_position)
                    self.assertEqual(tile.scale, original_scale)
                    self.assertFalse(v.isAnimating)

    def test_final_level_returns_to_visible_completion_without_loading_eleven(self):
        from test_gui_rules import make_view, finish_movement, finish_roll
        v = make_view()
        v.levelManager.currentLevel = v.levelManager.maxLevel
        v.levelManager.loadLevel = Mock(side_effect=AssertionError('Must not load a nonexistent level'))
        v.beginMove(D.RIGHT)
        finish_roll(v)
        v.beginMove(D.RIGHT)
        finish_roll(v)
        finish_movement(v)
        v.updateAnimations(1)
        self.assertEqual(v.levelManager.currentLevel, 10)
        v.levelManager.loadLevel.assert_not_called()
        self.assertIn('All levels completed', v.solverMessage.text)
        self.assertFalse(v.winBlackout.enabled)
        self.assertTrue(v.blockMesh.enabled)
        self.assertEqual(v.blockMesh.position, (4,0,-1))
        self.assertFalse(v.beginMove(D.LEFT))
        self.assertIn('All levels completed', v.solverMessage.text)
