from copy import deepcopy
from pathlib import Path
import sys
import tracemalloc
import unittest
from unittest.mock import patch

from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Board, Tile as T
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from inputHandler import InputHandler, Utility
from levels.levelLoader import loadLevelFromJson
from levels.levelManager import LevelManager
from runner import RunResult, run_search
from search.contracts import SearchLimits, SearchResult
from search.registry import get_solver

ROOT = Path(__file__).resolve().parents[1]


class EngineTests(unittest.TestCase):
    def test_nested_copy_and_sibling_independence(self):
        board = Board(7, 7)
        board.setTile(3, 4, T.SOFT_SWITCH)
        board.addBridge((3, 4), [(0, 0)])
        board.bridgeMap[(3, 4)] = {"nested": [1]}
        parent = State(board, Block(3, 3))
        before = deepcopy(parent)
        problem = Problem(parent)
        first = problem.result(parent, D.RIGHT)
        self.assertFalse(first.board.bridgeState[(3, 4)])
        snapshot = deepcopy(first)
        second = problem.result(parent, D.DOWN)
        self.assertEqual(parent, before)
        self.assertEqual(first, snapshot)
        second.board.bridgeGroups[(3, 4)].append((1, 1))
        second.board.initialTiles[0][0] = T.VOID
        second.board.bridgeMap[(3, 4)]["nested"].append(2)
        self.assertEqual(board.__dict__, before.board.__dict__)
        self.assertEqual(first.board.__dict__, snapshot.board.__dict__)

    def test_equality_hash_dynamic_bridges_and_orientation(self):
        state = State(Board(3, 3), Block(1, 1))
        state.board.addBridge((0, 0), [(2, 2)])
        copied = state.copy()
        self.assertEqual(state, copied)
        self.assertEqual(hash(state), hash(copied))
        copied.board.bridgeState[(0, 0)] = False
        self.assertEqual(state.board.tiles, copied.board.tiles)
        self.assertNotEqual(state, copied)
        self.assertEqual(len({state, copied}), 2)
        copied = state.copy()
        copied.block.orientation = O.LYING
        self.assertNotEqual(state, copied)

    def test_all_basic_rolls(self):
        cases = [
            (Block(3, 3), [(1,3,1,0,O.LYING),(4,3,1,0,O.LYING),(3,1,0,1,O.LYING),(3,4,0,1,O.LYING)]),
            (Block(3,3,0,1,O.LYING), [(2,3,0,1,O.LYING),(4,3,0,1,O.LYING),(3,2,0,0,O.STANDING),(3,5,0,0,O.STANDING)]),
            (Block(3,3,1,0,O.LYING), [(2,3,0,0,O.STANDING),(5,3,0,0,O.STANDING),(3,2,1,0,O.LYING),(3,4,1,0,O.LYING)]),
        ]
        for block, expected in cases:
            for direction, fields in zip(D, expected):
                with self.subTest(block=block, direction=direction):
                    self.assertEqual(block.resultingState(direction), Block(*fields))

    def test_invalid_moves_and_complete_goal(self):
        board = Board(4, 5)
        problem = Problem(State(board, Block(0, 0)))
        self.assertIsNone(problem.result(problem.initial, D.UP))
        board.setTile(0, 3, T.FRAGILE)
        self.assertIsNone(problem.result(State(board, Block(0,1,0,1,O.LYING)), D.RIGHT))
        board.setTile(1, 1, T.GOAL)
        self.assertTrue(problem.goal_test(State(board, Block(1, 1))))
        self.assertFalse(problem.goal_test(State(board, Block(1,1,0,1,O.LYING))))
        self.assertFalse(problem.goal_test(State(board, Block(1,1,1,0,O.STANDING))))

    def test_switch_removing_support_matches_controller(self):
        board = Board(3, 5)
        board.setTile(1, 2, T.SOFT_SWITCH)
        board.addBridge((1, 2), [(1, 3)])
        state = State(board, Block(1, 1)).copy()
        self.assertIsNone(Problem(state).result(state, D.RIGHT))
        game = GameController(board, Block(1, 1))
        self.assertFalse(game.executeMove(D.RIGHT))
        self.assertTrue(game.isGameOver)

    def test_loader_replay_cost_and_reset(self):
        board, block = loadLevelFromJson(ROOT / 'levels/level1.json', isDebug=False)
        game = GameController(board, block)
        problem = Problem(State(board, block).copy())
        state, cost = problem.initial, 0
        self.assertEqual(problem.actions(state), list(D))
        for action in (D.RIGHT, D.RIGHT):
            child = problem.result(state, action)
            cost += problem.step_cost(state, action, child)
            self.assertEqual(Problem(state, unit_cost=True).step_cost(state, action, child), 1)
            self.assertTrue(game.executeMove(action))
            self.assertEqual(child, State(game.board, game.block))
            state = child
        self.assertTrue(problem.goal_test(state))
        self.assertTrue(game.hasWon)
        self.assertEqual(cost, 2)
        game.reset()
        self.assertEqual(State(game.board, game.block), problem.initial)
        self.assertFalse(game.hasWon)

    def test_level_files_and_end(self):
        manager = LevelManager()
        for number in range(1, manager.maxLevel + 1):
            board, block = loadLevelFromJson(ROOT / f'levels/level{number}.json', isDebug=False)
            self.assertEqual(len(board.tiles), board.rows)
            self.assertTrue(all(len(row) == board.cols for row in board.tiles))
        manager.currentLevel = manager.maxLevel
        self.assertIsNone(manager.nextLevel())

    def test_reset_restores_loaded_bridge_configuration(self):
        for number in range(1, 12):
            with self.subTest(level=number):
                board, _ = loadLevelFromJson(ROOT / f'levels/level{number}.json', isDebug=False)
                initial_tiles = deepcopy(board.tiles)
                initial_bridges = board.bridgeState.copy()
                for _ in range(2):
                    for switch in board.bridgeGroups:
                        board.toggleBridge(switch)
                    board.setTile(0, 0, T.FRAGILE)
                    board.bridgeState[(-1, -1)] = False
                    board.reset()
                    self.assertEqual(board.tiles, initial_tiles)
                    self.assertEqual(board.bridgeState, initial_bridges)
                    self.assertEqual(board.initialBridgeState, initial_bridges)
                    self.assertIsNot(board.bridgeState, board.initialBridgeState)

    def test_keyboard_routes(self):
        handler = InputHandler()
        self.assertIs(handler.processKeyDirection('w'), D.UP)
        self.assertIsNone(handler.processKeyUtility('w'))
        self.assertIsNone(handler.processKeyDirection('w up'))
        self.assertIs(handler.processKeyUtility('r'), Utility.RESTART)
        self.assertIsNone(handler.processKeyDirection('r'))
        self.assertIsNone(handler.processKeyUtility('r up'))
        self.assertIsNone(handler.processKeyUtility('p up'))
        self.assertIsNone(handler.processKeyUtility('escape up'))
        self.assertIs(handler.processKeyDirection('right arrow'), D.RIGHT)
        self.assertIsNone(handler.processKeyDirection('right arrow up'))


class RunnerTests(unittest.TestCase):
    def test_registry_stubs_never_fallback(self):
        self.assertIs(get_solver('A*'), get_solver('astar'))
        with self.assertRaises(ValueError):
            get_solver('missing')
        for name in ('dfs','ucs','astar'):
            with self.subTest(name=name), self.assertRaises(NotImplementedError):
                run_search(object(), name, SearchLimits())
            self.assertFalse(tracemalloc.is_tracing())

    def test_runner_passes_contract_and_measures(self):
        problem, heuristic = object(), object()
        limits = SearchLimits()
        for status in ('solved', 'unsolvable', 'timeout', 'node_limit'):
            expected = SearchResult(status, (D.RIGHT,) if status == 'solved' else (), 1.0 if status == 'solved' else None, 2, 3)
            def fake(p, lim, h):
                self.assertIs(p, problem)
                self.assertIs(lim, limits)
                self.assertIs(h, heuristic)
                self.assertTrue(tracemalloc.is_tracing())
                allocation = bytearray(10000)
                return expected
            with patch.dict('search.registry.SOLVERS', {'fixture': fake}):
                result = run_search(problem, 'fixture', limits, heuristic)
            self.assertIsInstance(result, RunResult)
            self.assertIs(result.search, expected)
            self.assertGreaterEqual(result.search_time_seconds, 0)
            self.assertGreaterEqual(result.peak_memory_bytes, 10000)
            self.assertFalse(tracemalloc.is_tracing())

    def test_errors_cleanup_and_invalid_limits(self):
        def broken(*args):
            raise RuntimeError('fixture error')
        with patch.dict('search.registry.SOLVERS', {'fixture': broken}):
            with self.assertRaisesRegex(RuntimeError, 'fixture error'):
                run_search(None, 'fixture', SearchLimits())
        self.assertFalse(tracemalloc.is_tracing())
        with patch.dict('search.registry.SOLVERS', {'fixture': lambda *args: None}):
            with self.assertRaises(TypeError):
                run_search(None, 'fixture', SearchLimits())
        for limits in (SearchLimits(0), SearchLimits(float('inf')), SearchLimits(max_expanded_nodes=-1)):
            with self.assertRaises(ValueError):
                run_search(None, 'bfs', limits)

    def test_existing_trace_is_preserved_and_nested_run_rejected(self):
        tracemalloc.start()
        try:
            with self.assertRaisesRegex(RuntimeError, 'already active'):
                run_search(None, 'bfs', SearchLimits())
            self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()
        def nested(*args):
            return run_search(None, 'bfs', SearchLimits())
        with patch.dict('search.registry.SOLVERS', {'nested': nested}):
            with self.assertRaisesRegex(RuntimeError, 'Another search'):
                run_search(None, 'nested', SearchLimits())
        self.assertFalse(tracemalloc.is_tracing())

    def test_headless_does_not_import_ursina(self):
        self.assertNotIn('ursina', sys.modules)


if __name__ == '__main__':
    unittest.main()
