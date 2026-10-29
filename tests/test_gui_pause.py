"""Pause/replacement regressions during search, rolling and replay delay."""
import importlib.util
import unittest
from concurrent.futures import CancelledError
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch

from test_gui_rules import make_view, finish_roll
from gameModel.block import Direction as D
from inputHandler import InputHandler
from runner import run_search


def playable():
    v = make_view(13)
    v.inputHandler = InputHandler()
    v.pauseMenu = SimpleNamespace(enabled=False)
    v.pauseMenu.disable = lambda: setattr(v.pauseMenu, 'enabled', False)
    v.solverMenu = SimpleNamespace(enabled=False)
    v.solverMenu.hide = lambda: setattr(v.solverMenu, 'enabled', False)
    v.solverMenu.show = lambda: setattr(v.solverMenu, 'enabled', True)
    return v


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class PauseTests(unittest.TestCase):
    def test_p_freezes_half_roll_and_resumes_same_move(self):
        v = playable()
        v.isSolving = True
        v.autoSolution = [D.RIGHT, D.DOWN]
        v.queueReplay()
        v.updateAnimations(0)
        v.updateAnimations(.11)
        pose = (v.blockMesh.position, v.blockMesh.rotation)
        v.handleUrsinaInput('p')
        self.assertTrue(v.pauseMenu.enabled and v.isPaused)
        v.updateAnimations(100)
        self.assertEqual((v.blockMesh.position, v.blockMesh.rotation), pose)
        self.assertEqual(v.autoIndex, 1)
        v.handleUrsinaInput('p')
        finish_roll(v)
        self.assertFalse(v.isAnimating or v.isPaused)
        self.assertEqual(v.autoIndex, 1)

    def test_solver_and_menu_freeze_replay_delay(self):
        v = playable()
        v.isSolving = True
        v.autoSolution = [D.RIGHT]
        v._replayRemaining = .5
        v.queueReplay()
        v.showSolverMenu()
        v.updateAnimations(10)
        self.assertEqual(v._replayRemaining, .5)
        v.togglePause()
        self.assertTrue(v.pauseMenu.enabled)
        self.assertFalse(v.solverMenu.enabled)
        v.handleUrsinaInput('p')
        v.updateAnimations(.5)
        self.assertEqual(v.autoIndex, 1)

    def test_replace_half_roll_searches_from_landing_without_old_next_move(self):
        v = playable()
        v.isSolving = True
        v.autoSolution = [D.RIGHT, D.DOWN]
        v.queueReplay()
        v.updateAnimations(0)
        v.updateAnimations(.11)
        v.showSolverMenu()
        with patch.object(v, 'solve') as solve:
            v.handleAlgorithmSelected('UCS')
            solve.assert_not_called()
            finish_roll(v)
            solve.assert_called_once_with('ucs')
        self.assertFalse(v._replayReady)
        self.assertEqual(v.moveCount, 1)

    def test_slow_search_is_responsive_and_replacement_discards_old_result(self):
        v = playable()
        entered, release = Event(), Event()
        def slow(problem, *args, **kwargs):
            entered.set()
            release.wait(5)
            problem.checkpoint()
            return run_search(problem, *args, **kwargs)
        with patch('view.run_search', side_effect=slow):
            v.solve('dfs')
            old = v._searchJob
            self.assertTrue(entered.wait(2))
            v.handleUrsinaInput('p')
            self.assertTrue(v.pauseMenu.enabled)
            v.showSolverMenu()
            v.handleAlgorithmSelected('BFS')
            new = v._searchJob
            release.set()
            with self.assertRaises(CancelledError):
                old.future.result(timeout=5)
            new.future.result(timeout=10)
            v.pollSearch()
        self.assertIn('bfs: solved', v.solverMessage.text)
        self.assertEqual(v.autoIndex, 0)
        v.restartLevel()
        v.updateAnimations(10)
        self.assertFalse(v.isSolving)
