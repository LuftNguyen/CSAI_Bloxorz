"""DFS acceptance tests for CONTRACT V1; no GUI dependencies required.

Run from the repository root:
    python -m unittest discover -s tests -p "test_dfs.py" -v

These tests intentionally fail while search/dfs.py is still a stub.
"""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Block, Direction as D
from gameModel.board import Board, Tile as T
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search
from search import dfs
from search.contracts import SearchLimits, SearchResult


ROOT = Path(__file__).resolve().parents[1]


class GraphProblem:
    """Small directed graph exposing only the shared Problem interface.

    Edges are (Direction, destination or None, cost), in the desired order.
    The attempt guard makes broken cycle handling fail without hanging tests.
    """

    def __init__(self, edges, *, initial="start", goals=()):
        self.initial = initial
        self.edges = edges
        self.goals = set(goals)
        self.expansions = []
        self.attempts = []
        self.on_result = None

    def actions(self, state):
        self.expansions.append(state)
        return iter(action for action, _, _ in self.edges.get(state, ()))

    def result(self, state, action):
        self.attempts.append((state, action))
        if len(self.attempts) > 100:
            raise AssertionError("Too many transitions: check DFS cycle handling")
        if self.on_result is not None:
            self.on_result(state, action)
        for candidate, child, _ in self.edges.get(state, ()):
            if candidate == action:
                return child
        raise AssertionError("Solver tried an action not supplied by actions()")

    def goal_test(self, state):
        return state in self.goals

    def step_cost(self, state, action, next_state):
        if next_state is None:
            raise AssertionError("Invalid successors must not be costed")
        for candidate, child, cost in self.edges.get(state, ()):
            if candidate == action and child == next_state:
                return cost
        raise AssertionError("Cost requested for an unknown transition")


class DfsContractTests(unittest.TestCase):
    def assert_result(self, result, status, actions=(), cost=None,
                      *, expanded=None, generated=None):
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.status, status)
        self.assertIsInstance(result.actions, tuple)
        self.assertEqual(result.actions, actions)
        self.assertTrue(all(isinstance(action, D) for action in result.actions))
        if cost is None:
            self.assertIsNone(result.total_cost)
        else:
            self.assertAlmostEqual(result.total_cost, cost)
        for value in (result.expanded_nodes, result.generated_nodes):
            self.assertIs(type(value), int)
            self.assertGreaterEqual(value, 0)
        if expanded is not None:
            self.assertEqual(result.expanded_nodes, expanded)
        if generated is not None:
            self.assertEqual(result.generated_nodes, generated)

    def test_initial_goal_precedes_zero_node_limit(self):
        problem = GraphProblem({}, goals={"start"})
        result = dfs.solve(problem, SearchLimits(max_expanded_nodes=0))
        self.assert_result(result, "solved", cost=0.0, expanded=0, generated=0)
        self.assertEqual(problem.expansions, [])

    def test_dead_end_is_unsolvable_and_counts_one_expansion(self):
        result = dfs.solve(GraphProblem({}), SearchLimits())
        self.assert_result(result, "unsolvable", expanded=1, generated=0)

    def test_ignores_invalid_successors_and_sums_nonuniform_costs(self):
        problem = GraphProblem({
            "start": [(D.LEFT, None, 99), (D.RIGHT, "middle", 0.5)],
            "middle": [(D.UP, "goal", 5.0)],
        }, goals={"goal"})
        result = dfs.solve(problem, SearchLimits())
        self.assert_result(result, "solved", (D.RIGHT, D.UP), 5.5,
                           expanded=2, generated=2)

    def test_depth_first_order_and_goal_check_on_pop(self):
        # UP reaches a shallow goal, but RIGHT is listed first and must be
        # explored to its deeper goal. Returning a goal on generation is wrong.
        problem = GraphProblem({
            "start": [(D.RIGHT, "branch", 1), (D.UP, "shallow_goal", 1)],
            "branch": [(D.LEFT, "deeper", 1)],
            "deeper": [(D.DOWN, "deep_goal", 1)],
        }, goals={"shallow_goal", "deep_goal"})
        result = dfs.solve(problem, SearchLimits())
        self.assert_result(result, "solved", (D.RIGHT, D.LEFT, D.DOWN), 3,
                           expanded=3, generated=4)
        self.assertEqual(problem.expansions, ["start", "branch", "deeper"])

    def test_cycles_and_shared_child_count_valid_edges_before_filtering(self):
        problem = GraphProblem({
            "start": [(D.UP, "a", 1), (D.DOWN, "b", 1), (D.LEFT, None, 1)],
            "a": [(D.UP, "start", 1), (D.RIGHT, "shared", 1)],
            "b": [(D.RIGHT, "shared", 1)],
            "shared": [(D.LEFT, "shared", 1)],
        })
        result = dfs.solve(problem, SearchLimits(max_expanded_nodes=10))
        self.assert_result(result, "unsolvable", expanded=4, generated=6)
        self.assertCountEqual(problem.expansions, ["start", "a", "b", "shared"])

    def test_backtracks_after_dead_end(self):
        problem = GraphProblem({
            "start": [(D.LEFT, "dead_end", 1), (D.RIGHT, "branch", 2)],
            "branch": [(D.UP, "goal", 3)],
        }, goals={"goal"})
        result = dfs.solve(problem, SearchLimits())
        self.assert_result(result, "solved", (D.RIGHT, D.UP), 5,
                           expanded=3, generated=3)
        self.assertEqual(problem.expansions, ["start", "dead_end", "branch"])

    def test_zero_node_limit_prevents_expansion(self):
        problem = GraphProblem({"start": [(D.RIGHT, "goal", 1)]}, goals={"goal"})
        result = dfs.solve(problem, SearchLimits(max_expanded_nodes=0))
        self.assert_result(result, "node_limit", expanded=0, generated=0)
        self.assertEqual(problem.attempts, [])

    def test_node_limit_stops_before_next_expansion(self):
        problem = GraphProblem({
            "start": [(D.RIGHT, "middle", 1)],
            "middle": [(D.RIGHT, "goal", 1)],
        }, goals={"goal"})
        result = dfs.solve(problem, SearchLimits(max_expanded_nodes=1))
        self.assert_result(result, "node_limit", expanded=1, generated=1)
        self.assertEqual(problem.expansions, ["start"])

    def test_popped_goal_precedes_exhausted_node_budget(self):
        problem = GraphProblem({"start": [(D.RIGHT, "goal", 2)]}, goals={"goal"})
        result = dfs.solve(problem, SearchLimits(max_expanded_nodes=1))
        self.assert_result(result, "solved", (D.RIGHT,), 2,
                           expanded=1, generated=1)

    def test_heuristic_is_ignored(self):
        heuristic = Mock(side_effect=AssertionError("DFS must ignore heuristic"))
        result = dfs.solve(GraphProblem({}, goals={"start"}), SearchLimits(), heuristic)
        self.assert_result(result, "solved", cost=0.0, expanded=0, generated=0)
        heuristic.assert_not_called()

    def test_engine_exception_is_not_converted_to_unsolvable(self):
        problem = GraphProblem({"start": [(D.RIGHT, "goal", 1)]})
        problem.on_result = Mock(side_effect=RuntimeError("transition failed"))
        with self.assertRaisesRegex(RuntimeError, "transition failed"):
            dfs.solve(problem, SearchLimits())

    def test_same_block_with_different_bridge_status_is_not_pruned(self):
        board = Board(1, 4)
        board.addBridge((0, 1), [(0, 2)])
        initial = State(board, Block(0, 0))
        changed = initial.copy()
        # Equal placements and tiles, but different dynamic state.
        changed.board.bridgeState[(0, 1)] = False
        goal = changed.copy()
        goal.block = Block(0, 3)
        self.assertEqual(initial.block, changed.block)
        self.assertEqual(initial.board.tiles, changed.board.tiles)
        self.assertNotEqual(initial, changed)
        problem = GraphProblem({
            initial: [(D.RIGHT, changed, 1)],
            changed: [(D.UP, goal, 1)],
        }, initial=initial, goals={goal})
        result = dfs.solve(problem, SearchLimits())
        self.assert_result(result, "solved", (D.RIGHT, D.UP), 2,
                           expanded=2, generated=2)

    def test_timeout_before_expansion(self):
        problem = GraphProblem({"start": [(D.RIGHT, "goal", 1)]}, goals={"goal"})
        # First read starts the clock; every later read is past the deadline.
        readings = iter((0.0,))
        clock = lambda: next(readings, 2.0)
        # Support either `from time import perf_counter` or `import time`.
        with patch("time.perf_counter", clock), patch.object(
                dfs, "perf_counter", clock, create=True):
            result = dfs.solve(problem, SearchLimits(timeout_seconds=1.0))
        self.assert_result(result, "timeout", expanded=0, generated=0)
        self.assertEqual(problem.attempts, [])

    def test_timeout_is_checked_between_successor_generations(self):
        problem = GraphProblem({
            "start": [(D.UP, "a", 1), (D.RIGHT, "b", 1)],
        })
        now = [0.0]

        def expire_after_first_transition(state, action):
            if len(problem.attempts) > 1:
                raise AssertionError("Timeout was not checked between successors")
            now[0] = 2.0

        problem.on_result = expire_after_first_transition
        clock = lambda: now[0]
        with patch("time.perf_counter", clock), patch.object(
                dfs, "perf_counter", clock, create=True):
            result = dfs.solve(problem, SearchLimits(timeout_seconds=1.0))
        self.assert_result(result, "timeout", expanded=1)
        self.assertEqual(len(problem.attempts), 1)


class DfsEngineTests(unittest.TestCase):
    def solve_and_replay(self, problem, *, via_runner=False):
        before = deepcopy(problem.initial)
        initial_hash = hash(problem.initial)
        limits = SearchLimits(timeout_seconds=5.0, max_expanded_nodes=5000)
        if via_runner:
            run = run_search(problem, "dfs", limits)
            result = run.search
            self.assertGreaterEqual(run.search_time_seconds, 0.0)
            self.assertGreater(run.peak_memory_bytes, 0)
        else:
            result = dfs.solve(problem, limits)
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.status, "solved")
        self.assertIsInstance(result.actions, tuple)
        self.assertGreater(len(result.actions), 0)
        self.assertEqual(problem.initial, before)
        self.assertEqual(problem.initial.board.__dict__, before.board.__dict__)
        self.assertEqual(hash(problem.initial), initial_hash)

        state = before.copy()
        game = GameController(deepcopy(before.board), before.block.copy())
        cost = 0.0
        for action in result.actions:
            self.assertIsInstance(action, D)
            child = problem.result(state, action)
            self.assertIsNotNone(child, f"Illegal replay move: {action}")
            cost += problem.step_cost(state, action, child)
            self.assertTrue(game.executeMove(action))
            self.assertEqual(child, State(game.board, game.block))
            state = child
        self.assertTrue(problem.goal_test(state))
        self.assertTrue(game.hasWon)
        self.assertAlmostEqual(result.total_cost, cost)
        self.assertEqual(problem.initial.board.__dict__, before.board.__dict__)
        self.assertEqual(problem.initial, before)
        return result

    def test_level_one_via_runner_replays_to_goal(self):
        board, block = loadLevelFromJson(ROOT / "levels/level1.json", isDebug=False)
        self.solve_and_replay(Problem(State(board, block).copy()), via_runner=True)

    def test_fragile_corridor_uses_shared_cost_function(self):
        board = Board(1, 4, [[T.NORMAL, T.FRAGILE, T.NORMAL, T.GOAL]])
        result = self.solve_and_replay(Problem(State(board, Block(0, 0))))
        self.assertEqual(result.actions, (D.RIGHT, D.RIGHT))
        self.assertAlmostEqual(result.total_cost, 6.0)

    def test_unit_cost_corridor(self):
        board = Board(1, 4, [[T.NORMAL, T.FRAGILE, T.NORMAL, T.GOAL]])
        result = self.solve_and_replay(Problem(State(board, Block(0, 0)), unit_cost=True))
        self.assertAlmostEqual(result.total_cost, 2.0)

    def test_soft_switch_opens_bridge_for_solution(self):
        board = Board(1, 7, [[
            T.NORMAL, T.SOFT_SWITCH, T.NORMAL, T.BRIDGE,
            T.NORMAL, T.NORMAL, T.GOAL,
        ]])
        board.addBridge((0, 1), [(0, 3)])
        board.toggleBridge((0, 1))  # Start with a closed bridge (VOID).
        result = self.solve_and_replay(Problem(State(board, Block(0, 0))))
        self.assertEqual(result.actions, (D.RIGHT,) * 4)

    def test_heavy_switch_opens_bridge_when_standing(self):
        board = Board(1, 7, [[
            T.NORMAL, T.NORMAL, T.NORMAL, T.HEAVY_SWITCH,
            T.BRIDGE, T.NORMAL, T.GOAL,
        ]])
        board.addBridge((0, 3), [(0, 4)])
        board.toggleBridge((0, 3))
        result = self.solve_and_replay(Problem(State(board, Block(0, 0))))
        self.assertEqual(result.actions, (D.RIGHT,) * 4)

    def test_fragile_tile_blocks_only_route_to_existing_goal(self):
        board = Board(1, 7, [[
            T.NORMAL, T.NORMAL, T.NORMAL, T.FRAGILE,
            T.NORMAL, T.NORMAL, T.GOAL,
        ]])
        result = dfs.solve(Problem(State(board, Block(0, 0))), SearchLimits())
        self.assertEqual(result.status, "unsolvable")
        self.assertEqual(result.actions, ())
        self.assertIsNone(result.total_cost)


if __name__ == "__main__":
    unittest.main()
