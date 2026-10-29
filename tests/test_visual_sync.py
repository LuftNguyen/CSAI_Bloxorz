"""Completion tests include the installed Ursina sequences, without a GUI window."""
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from unittest.mock import patch

from animation_sync import AnimationCompletion


class CompletionTests(unittest.TestCase):
    def test_waits_for_every_handle_and_final_assignment_once(self):
        a = SimpleNamespace(finished=True, func_finished_statuses=[True], kill=Mock())
        b = SimpleNamespace(finished=False, func_finished_statuses=[False], kill=Mock())
        done = Mock()
        group = AnimationCompletion([(a, None), b], done)
        group.poll()
        done.assert_not_called()
        b.finished = True
        group.poll()
        done.assert_not_called()  # The final setter still has not run.
        b.func_finished_statuses = [True]
        group.poll()
        group.poll()
        done.assert_called_once()

    def test_cancel_never_calls_completion(self):
        handle = SimpleNamespace(finished=True, func_finished_statuses=[True], kill=Mock())
        done = Mock()
        group = AnimationCompletion([handle], done)
        group.cancel()
        group.poll()
        handle.kill.assert_called_once()
        done.assert_not_called()


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class InstalledUrsinaCompletionTests(unittest.TestCase):
    def test_real_position_and_scale_sequences_outlive_nominal_duration(self):
        from ursina import Entity, curve
        entity = Entity(add_to_scene_entities=False)
        handles = [entity.animate_position((3,0,0), duration=0.4, curve=curve.linear),
                   entity.animate_scale((2,2,2), duration=0.5, curve=curve.linear)]
        done = Mock()
        group = AnimationCompletion(handles, done)
        try:
            for handle in group.handles:
                handle.time_step = 0.4
                handle.update()
            group.poll()
            done.assert_not_called()
            self.assertTrue(any(h.duration > 0.4 for h in group.handles))
            for handle in group.handles:
                handle.time_step = 0.03
                handle.update()
            group.poll()
            done.assert_not_called()  # Position finished, scale is still running.
            for handle in group.handles:
                handle.time_step = 0.1
                handle.update()
            group.poll()
            group.poll()
            done.assert_called_once()
            self.assertEqual(tuple(entity.position), (3,0,0))
            self.assertEqual(tuple(entity.scale), (2,2,2))
        finally:
            group.cancel()
            entity.removeNode()


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class PresentationOrderingTests(unittest.TestCase):
    def test_consecutive_rolling_replay_keeps_switch_visuals_consistent(self):
        from test_gui_rules import make_view, finish_roll
        from gameModel.block import Direction as D
        from gameModel.state import State
        v = make_view()
        shown = []
        v.renderBoard.side_effect = lambda: shown.append(State(v.gameModel.board,v.gameModel.block).copy())
        v.isSolving = True
        v.autoSolution = [D.RIGHT, D.DOWN, D.DOWN, D.RIGHT]
        execute = v.gameModel.executeMove = Mock(wraps=v.gameModel.executeMove)
        with patch('view.invoke') as invoke:
            v.queueReplay()
            for index in range(4):
                v.updateAnimations(0.5)
                self.assertEqual(v.autoIndex, index + 1)
                self.assertTrue(v.isAnimating)
                self.assertEqual(len(shown), index)
                finish_roll(v)
                self.assertFalse(v.isAnimating)
                self.assertIsNone(v._movement)
                self.assertEqual(execute.call_count, index + 1)
                self.assertEqual(shown[-1], State(v.gameModel.board,v.gameModel.block))
            self.assertTrue(shown[-1].board.bridgeState['lower_practice'])
            v.updateAnimations(0.5)
            invoke.assert_not_called()
        self.assertFalse(v.isSolving)
        v.blockMesh.animate_position.assert_not_called()
        v.blockMesh.animate_scale.assert_not_called()

    def test_manual_open_and_heavy_close_present_effects_after_landing_once(self):
        from test_gui_rules import make_view, finish_roll
        from gameModel.block import Block, Direction as D, Orientation as O
        for closing in (False, True):
            with self.subTest(closing=closing):
                v = make_view(13)
                if closing:
                    v.gameModel.board.applySwitch((1,2))
                    v.gameModel.block = Block(2,3,0,1,O.LYING)
                    v.updateBlockMesh()
                events = []
                update = v.updateBlockMesh
                v.updateBlockMesh = Mock(side_effect=lambda **kw: (events.append('pose'), update(**kw)))
                def render():
                    events.append('board')
                    self.assertEqual(v.gameModel.board.bridgeState['crossing'], not closing)
                    self.assertEqual(v.blockMesh.position, (2,0,-2) if closing else (2.5,0,-1))
                v.renderBoard.side_effect = render
                execute = v.gameModel.executeMove = Mock(wraps=v.gameModel.executeMove)
                self.assertTrue(v.beginMove(D.LEFT if closing else D.RIGHT))
                self.assertEqual(events, [])
                v.updateAnimations(v.rollDuration / 2)
                self.assertEqual(events, [])
                self.assertFalse(v.beginMove(D.DOWN))
                v.finishStep()  # A caller cannot skip the remaining roll.
                self.assertEqual(events, [])
                finish_roll(v)
                self.assertEqual(events, ['pose','board'])
                self.assertFalse(v.isAnimating)
                self.assertIsNone(v._movement)
                v.finishStep()
                v.renderBoard.assert_called_once()
                execute.assert_called_once()
                v.blockMesh.animate_position.assert_not_called()
                v.blockMesh.animate_scale.assert_not_called()

    def test_fragile_and_void_fall_start_from_final_pose_after_board_update(self):
        from test_gui_rules import make_view, finish_roll
        from gameModel.block import Block, Direction as D, Orientation as O
        from gameModel.board import Tile
        for fragile in (False, True):
            with self.subTest(fragile=fragile):
                v = make_view()
                if fragile:
                    v.gameModel.board.setTile(1,4,Tile.FRAGILE)
                    v.gameModel.block = Block(1,2,0,1,O.LYING)
                    v.updateBlockMesh()
                events = []
                v.renderBoard.side_effect = lambda: events.append('board')
                def fall(direction):
                    events.append('fall')
                    self.assertEqual(v.blockMesh.position, (4,0,-1) if fragile else (-0.5,0,-1))
                    if fragile:
                        self.assertEqual(v.gameModel.board.getTile(1,4), Tile.VOID)
                v.animateFall = Mock(side_effect=fall)
                v.beginMove(D.RIGHT if fragile else D.LEFT)
                self.assertTrue(v.gameModel.isGameOver)
                self.assertEqual(events, [])
                v.animateFall.assert_not_called()
                finish_roll(v)
                self.assertEqual(events, ['board','fall'])
                v.finishStep()
                v.animateFall.assert_called_once()
                v.blockMesh.animate_position.assert_not_called()
                v.blockMesh.animate_scale.assert_not_called()

    def test_fall_restart_waits_for_all_fall_handles(self):
        from test_gui_rules import make_view, finish_movement, finish_roll
        from gameModel.block import Direction as D
        v = make_view()
        with patch('view.invoke', return_value=SimpleNamespace(kill=Mock())) as invoke:
            v.beginMove(D.LEFT)
            finish_roll(v)
            fall = v._movement
            self.assertTrue(v.isAnimating)
            self.assertFalse(v.beginMove(D.RIGHT))
            invoke.assert_not_called()
            for handle in fall.handles[:-1]:
                handle.finished = True
                handle.func_finished_statuses = [True]
            v.updateAnimations()
            invoke.assert_not_called()
            finish_movement(v)
            self.assertEqual(invoke.call_args.kwargs['delay'], 0.1)
            v.updateAnimations()
            v.finishStep()
            invoke.assert_called_once()

    def test_split_and_merge_wait_for_landing_while_switch_stays_instant(self):
        from test_gui_rules import make_view, finish_roll
        from gameModel.block import Block, Direction as D, Orientation as O
        v = make_view(12)
        v.beginMove(D.RIGHT)
        finish_roll(v)
        self.assertFalse(v.isAnimating)
        v.beginMove(D.RIGHT)
        self.assertEqual(v.gameModel.block.orientation, O.SPLIT)
        self.assertTrue(v.blockMesh.enabled)
        self.assertFalse(any(m.enabled for m in v.cubeMeshes))
        finish_roll(v)
        self.assertFalse(v.blockMesh.enabled)
        self.assertTrue(all(m.enabled for m in v.cubeMeshes))
        self.assertEqual([m.position for m in v.cubeMeshes], [(1,0,-1),(6,0,-1)])
        old_color = v.cubeMeshes[1].color
        v.beginMove(D.SWITCH)
        self.assertEqual(v.gameModel.block.active, 1)
        self.assertIsNone(v._movement)
        self.assertNotEqual(v.cubeMeshes[1].color, old_color)
        v.gameModel.block = Block.split(((1,1),(1,3)))
        v.updateBlockMesh()
        v.beginMove(D.RIGHT)
        self.assertEqual(v.gameModel.block.orientation, O.LYING)
        self.assertFalse(v.blockMesh.enabled)
        self.assertTrue(all(m.enabled for m in v.cubeMeshes))
        inactive_position = v.cubeMeshes[1].position
        v.updateAnimations(v.rollDuration / 2)
        self.assertEqual(v.cubeMeshes[1].position, inactive_position)
        finish_roll(v)
        self.assertTrue(v.blockMesh.enabled)
        self.assertEqual(v.blockMesh.position, (2.5,0,-1))
        self.assertFalse(any(m.enabled for m in v.cubeMeshes))
        for mesh in [v.blockMesh]+v.cubeMeshes:
            mesh.animate_position.assert_not_called()
            mesh.animate_scale.assert_not_called()

    def test_manual_win_falls_then_blackout_before_level_change_once(self):
        from test_gui_rules import make_view, finish_movement, finish_roll
        from gameModel.block import Direction as D
        v = make_view()
        v.loadNextLevel = Mock()
        with patch('view.invoke', return_value=SimpleNamespace(kill=Mock())) as invoke:
            v.beginMove(D.RIGHT)
            finish_roll(v)
            invoke.assert_not_called()
            v.renderBoard.reset_mock()
            v.beginMove(D.RIGHT)
            self.assertIsNone(v._winPhase)
            finish_roll(v)
            self.assertTrue(v.gameModel.hasWon)
            self.assertEqual(v.blockMesh.position, (4,0,-1))
            v.renderBoard.assert_called_once()
            self.assertEqual(v.blockMesh.animate_y.call_args.args[0], -3.5)
            self.assertEqual(v.blockMesh.animate_y.call_args.kwargs['duration'], 0.6)
            self.assertEqual(v._winPhase, 'fall')
            v.finishStep()
            v.updateAnimations()
            invoke.assert_not_called()
            v.loadNextLevel.assert_not_called()
            finish_movement(v)
            self.assertTrue(v.winBlackout.enabled)
            v.updateAnimations(0.99)
            v.loadNextLevel.assert_not_called()
            v.updateAnimations(0.01)
            v.loadNextLevel.assert_called_once()

    def test_restart_and_level_change_reject_old_fall_completion_and_timer(self):
        from test_gui_rules import make_view, finish_roll
        from gameModel.block import Direction as D
        from levels.levelLoader import loadLevelFromJson
        from pathlib import Path
        for change_level in (False, True):
            with self.subTest(change_level=change_level):
                v = make_view()
                with patch('view.invoke', return_value=SimpleNamespace(kill=Mock())) as invoke:
                    delayed = Mock()
                    v.schedule(delayed, 2)
                    stale_timer = invoke.call_args.args[0]
                    v.beginMove(D.LEFT)
                    finish_roll(v)
                    group = v._movement
                    stale_completion = group.callback
                    if change_level:
                        path = Path(__file__).resolve().parents[1]/'tests/fixtures/legacy/level13.json'
                        v.changeLevel(loadLevelFromJson(path, False))
                    else:
                        v.restartLevel()
                    calls_after_reset = v.renderBoard.call_count
                    state_after = v.gameModel.block.copy()
                    stale_timer()
                    stale_completion()
                    group.poll()
                    self.assertEqual(v.renderBoard.call_count, calls_after_reset)
                    self.assertEqual(v.gameModel.block, state_after)
                    self.assertFalse(v.isAnimating or v.isSolving)
                    delayed.assert_not_called()
                    for handle in group.handles:
                        handle.kill.assert_called()

    def test_restart_cancels_queued_replay_without_an_extra_transition(self):
        from test_gui_rules import make_view
        from gameModel.block import Direction as D
        v = make_view()
        execute = v.gameModel.executeMove = Mock(wraps=v.gameModel.executeMove)
        v.isSolving = True
        v.autoSolution = [D.RIGHT,D.RIGHT]
        v.queueReplay()
        v.updateAnimations()
        self.assertEqual(execute.call_count, 1)
        self.assertIsNotNone(v._roll)
        v.restartLevel()
        v.updateAnimations()
        self.assertEqual(execute.call_count, 1)
        self.assertEqual((v.gameModel.block.r,v.gameModel.block.c), (1,1))
        self.assertFalse(v.isAnimating or v.isSolving or v._replayReady)

    def test_restart_and_level_change_cancel_a_half_finished_roll(self):
        from test_gui_rules import ROOT, make_view
        from gameModel.block import Direction as D
        from levels.levelLoader import loadLevelFromJson
        for change in (False, True):
            with self.subTest(change=change):
                v = make_view(13)
                v.beginMove(D.RIGHT)
                roll = v._roll
                v.updateAnimations(v.rollDuration / 2)
                self.assertNotEqual(v.blockMesh.rotation, (0,0,0))
                if change:
                    v.changeLevel(loadLevelFromJson(ROOT/'levels/level1.json', False))
                else:
                    v.restartLevel()
                pose = (v.blockMesh.position, v.blockMesh.rotation, v.blockMesh.scale)
                renders = v.renderBoard.call_count
                self.assertFalse(roll.advance(10))
                v.updateAnimations(10)
                self.assertEqual((v.blockMesh.position, v.blockMesh.rotation, v.blockMesh.scale), pose)
                self.assertEqual(v.renderBoard.call_count, renders)
                self.assertEqual(v.blockMesh.rotation, (0,0,0))
                self.assertIsNone(v._roll)
                self.assertFalse(v.isAnimating or v.isSolving)
