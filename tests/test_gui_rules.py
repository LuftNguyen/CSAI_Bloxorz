"""GUI orchestration with fake meshes/timers; never claims visual acceptance."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Tile as T
from gameModel.gameController import GameController
from gameModel.state import State
from gameModel.problem import Problem
from levels.levelLoader import loadLevelFromJson
from levels.levelManager import LevelManager
from runner import RunResult
from search.contracts import SearchResult

ROOT = Path(__file__).resolve().parents[1]


def animation_handle():
    return SimpleNamespace(finished=False, func_finished_statuses=[False], kill=Mock())


def finish_movement(view):
    for handle in view._movement.handles:
        handle.finished = True
        handle.func_finished_statuses = [True]
    view.updateAnimations()


def finish_roll(view):
    if getattr(view, '_roll', None) is not None:
        view.updateAnimations(view.rollDuration)


def mesh(enabled=True):
    return SimpleNamespace(enabled=enabled, position=(1,0,-1), scale=(0.9,1.9,0.9),
                           rotation=(0,0,0), rotation_x=0, rotation_z=0, y=0, color=None, animations=[],
                           animate_position=Mock(side_effect=lambda *a, **k: tuple(animation_handle() for _ in range(3))),
                           animate_scale=Mock(side_effect=lambda *a, **k: animation_handle()),
                           animate_y=Mock(side_effect=lambda *a, **k: animation_handle()),
                           animate_rotation_x=Mock(side_effect=lambda *a, **k: animation_handle()),
                           animate_rotation_z=Mock(side_effect=lambda *a, **k: animation_handle()))


def make_view(number=1):
    from view import BloxorzView
    v = BloxorzView.__new__(BloxorzView)
    b, block = loadLevelFromJson(ROOT/f'tests/fixtures/legacy/level{number}.json', False)
    v.gameModel = GameController(b, block)
    v.problem = Problem(State(b,block).copy())
    v.gameStarted = True
    v.isPaused = v.isAnimating = v.isSolving = False
    v._pendingCalls = []
    v._movement = None
    v._roll = None
    v.rollDuration = .22
    v._replayReady = False
    v.replayInterval = 0.5
    v._replayRemaining = 0.0
    v._presentingMove = False
    v._winPhase = v._blackoutRemaining = None
    v._winTilePoses = []
    v.winBlackout = SimpleNamespace(enabled=False)
    v.effectTileEntities = []
    from classic_theme import ClassicTheme
    v.theme = ClassicTheme.__new__(ClassicTheme)
    v.theme.slab = None
    v.theme.textures = dict.fromkeys(['limestone','fragile_stone','oxidized_metal','soft_shadow'])
    v.blockMesh = mesh()
    v.cubeMeshes = [mesh(False), mesh(False)]
    v.pauseMenu = SimpleNamespace(disable=Mock())
    v.solverMenu = SimpleNamespace(hide=Mock())
    v.solverMessage = SimpleNamespace(text='')
    v.levelManager = LevelManager()
    v.destroyTileEntities = Mock()
    v.renderBoard = Mock()
    v.setupCamera = Mock()
    v.autoSolution = []
    v.autoIndex = 0
    return v


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class GuiRulesTests(unittest.TestCase):
    def test_snapshot_independent_and_bad_solution_not_replayed(self):
        v = make_view()
        def fake(p, *args, **kwargs):
            self.assertIsNot(p.initial.board, v.gameModel.board)
            self.assertIsNot(p.initial.block, v.gameModel.block)
            self.assertIsNot(p.initial.board.tiles[0], v.gameModel.board.tiles[0])
            return RunResult(SearchResult('solved', (D.LEFT,), 1.0, 0, 0), 0.0, 0)
        with patch('view.run_search', side_effect=fake), patch('view.invoke') as invoke:
            v.solve('astar')
            self.assertIn('Solver error', v.solverMessage.text)
            self.assertFalse(v.isSolving)
            invoke.assert_not_called()

    def test_replay_waits_for_roll_then_full_pause_before_next_action(self):
        v = make_view()
        v.isSolving = True
        v.autoSolution = [D.RIGHT, D.RIGHT]
        v.loadNextLevel = Mock()
        with patch('view.invoke') as invoke:
            v.queueReplay()
            self.assertEqual(v.autoIndex, 0)
            v.updateAnimations(0)
            self.assertEqual(v.autoIndex, 1)
            self.assertTrue(v.isAnimating)
            self.assertEqual(v.blockMesh.position, (1,0,-1))
            v.updateAnimations(.11)
            self.assertEqual(v.blockMesh.rotation, (0,0,45))
            v.updateAnimations(.11)
            self.assertEqual(v.blockMesh.position, (2.5,0,-1))
            self.assertFalse(v.isAnimating)
            self.assertIsNone(v._movement)
            v.updateAnimations(0.49)
            self.assertEqual(v.autoIndex, 1)
            self.assertEqual(v.blockMesh.position, (2.5,0,-1))
            v.updateAnimations(0.01)
            self.assertEqual(v.autoIndex, 2)
            self.assertTrue(v.gameModel.hasWon)
            self.assertIsNone(v._winPhase)
            finish_roll(v)
            self.assertEqual(v.blockMesh.position, (4,0,-1))
            self.assertTrue(v.isAnimating)
            self.assertEqual(v._winPhase, 'fall')
            v.updateAnimations(0.5)
            self.assertFalse(v.isSolving)
            v.loadNextLevel.assert_not_called()
            finish_movement(v)
            self.assertTrue(v.winBlackout.enabled)
            v.updateAnimations(0.99)
            v.loadNextLevel.assert_not_called()
            v.updateAnimations(0.01)
            v.loadNextLevel.assert_called_once()
            invoke.assert_not_called()
        v.blockMesh.animate_position.assert_not_called()
        v.blockMesh.animate_scale.assert_not_called()

    def test_restart_cancels_calls_and_animations_restores_split(self):
        v = make_view(12)
        v.gameModel.executeMove(D.RIGHT)
        v.gameModel.executeMove(D.RIGHT)
        self.assertEqual(v.gameModel.block.orientation, O.SPLIT)
        timer, animation = SimpleNamespace(kill=Mock()), SimpleNamespace(kill=Mock())
        v._pendingCalls = [timer]
        v.cubeMeshes[0].animations = [animation]
        v.isSolving = v.isAnimating = True
        v.restartLevel()
        timer.kill.assert_called_once()
        animation.kill.assert_called_once()
        self.assertFalse(v.isSolving or v.isAnimating)
        self.assertEqual(v.gameModel.block.orientation, O.STANDING)
        self.assertEqual(v.gameModel.block.cubes, ())
        self.assertTrue(v.blockMesh.enabled)
        self.assertFalse(v.cubeMeshes[0].enabled)

    def test_change_level_cancels_old_calls_and_clears_split(self):
        v = make_view(12)
        v.gameModel.block = Block.split(((1,1),(1,6)))
        timer = SimpleNamespace(kill=Mock())
        v._pendingCalls = [timer]
        v.changeLevel(loadLevelFromJson(ROOT/'tests/fixtures/legacy/level13.json', False))
        timer.kill.assert_called_once()
        self.assertEqual(v.gameModel.block.orientation, O.STANDING)
        self.assertFalse(v.gameModel.board.bridgeState['crossing'])

    def test_two_cube_visuals_and_switch_highlight(self):
        from ursina import color
        v = make_view(12)
        v.gameModel.block = Block.split(((1,1),(1,6)))
        v.updateBlockMesh()
        self.assertFalse(v.blockMesh.enabled)
        self.assertTrue(all(m.enabled for m in v.cubeMeshes))
        self.assertEqual(v.cubeMeshes[0].position, (1,0,-1))
        self.assertEqual(v.cubeMeshes[0].color, color.yellow)
        v.gameModel.executeMove(D.SWITCH)
        v.updateBlockMesh()
        self.assertEqual(v.cubeMeshes[1].color, color.yellow)

    def test_bridge_disappears_with_shadow_when_closed_and_returns_when_open(self):
        from view import BloxorzView
        v = make_view(13)
        board = v.gameModel.board
        for switch, visible in ((None, False), ((1,2), True), ((2,2), False)):
            with self.subTest(switch=switch, visible=visible):
                if switch is not None:
                    board.applySwitch(switch)
                before = State(board, v.gameModel.block).copy()
                v.tileEntities = []
                with patch('classic_theme.Entity', side_effect=lambda **kwargs: SimpleNamespace(**kwargs)), patch('classic_theme.Text'):
                    BloxorzView.renderBoard(v)
                positions = [e.position for e in v.tileEntities]
                self.assertEqual(positions.count((4,-.1,-2)), int(visible))
                self.assertEqual(positions.count((4.16,-.75,-2.12)), int(visible))
                self.assertEqual(State(board, v.gameModel.block), before)

    def test_split_marker_rendered(self):
        from view import BloxorzView
        v = make_view(12)
        v.tileEntities = []
        v.tileColors = {}
        with patch('classic_theme.Entity') as entity, patch('classic_theme.Text'):
            BloxorzView.renderBoard(v)
            self.assertTrue(any(call.kwargs.get('scale') == (.22,.06,.50) for call in entity.call_args_list))

    def test_goal_is_one_recessed_classic_hole_and_void_stays_empty(self):
        from view import BloxorzView
        from ursina import color
        v = make_view(13)
        before = State(v.gameModel.board, v.gameModel.block).copy()
        v.tileEntities = []
        v.tileColors = {}
        with patch('classic_theme.Entity', side_effect=lambda **kwargs: SimpleNamespace(**kwargs)) as entity, patch('classic_theme.Text'):
            BloxorzView.renderBoard(v)
        calls = [c.kwargs for c in entity.call_args_list]
        holes = [c for c in calls if c.get('name') == 'goal_hole']
        self.assertEqual(len(holes), 1)
        self.assertEqual(holes[0]['position'], (7, -0.1, -1))
        self.assertNotIn('model', holes[0])  # No solid tile filling the opening.
        rims = [c for c in calls if c.get('name') == 'goal_rim']
        self.assertEqual(len(rims), 4)
        self.assertTrue(all(c['color'] == color.hex('#b89b60') for c in rims))
        bottom = next(c for c in calls if c.get('name') == 'goal_bottom')
        self.assertLess(bottom['position'][1], 0)
        self.assertFalse(any(c.get('position') == (0, -0.1, 0) and 'parent' not in c for c in calls))
        self.assertEqual(State(v.gameModel.board, v.gameModel.block), before)
