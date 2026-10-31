"""UCS contract, weighted optimality and headless integration regressions."""
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
import tracemalloc
import unittest
from unittest import result
from unittest.mock import Mock, patch

from gameModel.block import Block, Direction as D
from gameModel.board import Board, Tile as T, FRAGILE_PENALTY
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import RunResult, run_search
from search.contracts import SearchLimits, SearchResult
from search.registry import get_solver
from search.ucs import solve


@dataclass(frozen=True)
class _Vertex:
    """Hashable graph vertex deliberately lacking ordering for heap tie tests."""
    name: str


class _GraphProblem:
    """Five-interface test double; edges are (Direction, target name, cost)."""

    def __init__(self, edges, initial="S", goals=("G",)):
        self.initial = _Vertex(initial)
        self.edges = edges
        self.goals = set(goals)
        self.expansions = []
        self.goal_checks = []
        self.cost_calls = []

    def actions(self, state):
        self.expansions.append(state.name)
        # An ordered generator also checks that UCS does not require a list.
        return (action for action, _, _ in self.edges.get(state.name, ()))

    def result(self, state, action):
        for edge_action, target, _ in self.edges.get(state.name, ()):
            if edge_action == action:
                # Return equal but independent objects on repeated-state edges.
                return None if target is None else _Vertex(target)
        raise AssertionError("Solver tried an action not supplied by actions()")

    def goal_test(self, state):
        self.goal_checks.append(state.name)
        return state.name in self.goals

    def step_cost(self, state, action, child):
        self.cost_calls.append((state.name, action, child.name))
        for edge_action, target, cost in self.edges.get(state.name, ()):
            if edge_action == action:
                assert target is not None and child.name == target
                return cost
        raise AssertionError("Cost requested for an unknown transition")


class _Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def _weighted_problem(unit_cost=False):
    board = Board(3, 7, [
        [T.NORMAL, T.FRAGILE, T.NORMAL, T.NORMAL, T.FRAGILE, T.NORMAL, T.GOAL],
        [T.NORMAL] * 7,
        [T.NORMAL] * 7,
    ])
    return Problem(State(board, Block(0, 0)), unit_cost=unit_cost)


class UCSGraphTests(unittest.TestCase):
    def assert_result(self, result, status, cost, expanded, generated):
        self.assertIsInstance(result, SearchResult)
        self.assertEqual(result.status, status)
        self.assertIsInstance(result.actions, tuple)
        self.assertEqual(result.total_cost, cost)
        self.assertEqual(result.expanded_nodes, expanded)
        self.assertEqual(result.generated_nodes, generated)
        if status != "solved":
            self.assertEqual(result.actions, ())

    def assert_graph_replay(self, problem, result):
        state, cost = problem.initial, 0.0
        for action in result.actions:
            self.assertIsInstance(action, D)
            child = problem.result(state, action)
            self.assertIsNotNone(child)
            cost += problem.step_cost(state, action, child)
            state = child
        self.assertTrue(problem.goal_test(state))
        self.assertEqual(cost, result.total_cost)

    def test_initial_goal_with_zero_budget(self):
        problem = _GraphProblem({}, initial="G")
        result = solve(problem, SearchLimits(max_expanded_nodes=0))
        self.assert_result(result, "solved", 0.0, 0, 0)
        self.assertEqual(result.actions, ())
        self.assertEqual(problem.expansions, [])

    def test_simple_solution_and_goal_not_expanded(self):
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 0.5)]})
        result = solve(problem, SearchLimits())
        self.assert_result(result, "solved", 0.5, 1, 1)
        self.assertEqual(problem.expansions, ["S"])
        self.assert_graph_replay(problem, result)

    def test_unsolvable_dead_end(self):
        result = solve(_GraphProblem({}), SearchLimits())
        self.assert_result(result, "unsolvable", None, 1, 0)

    def test_cycle_counts_valid_duplicate_without_reexpanding(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "A", 1)],
            "A": [(D.LEFT, "S", 1)],
        })
        result = solve(problem, SearchLimits())
        self.assert_result(result, "unsolvable", None, 2, 2)
        self.assertEqual(problem.expansions, ["S", "A"])

    def test_w1_expensive_goal_discovered_before_cheaper_longer_path(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "G", 9), (D.DOWN, "A", 1)],
            "A": [(D.RIGHT, "B", 1)],
            "B": [(D.RIGHT, "G", 1)],
        })
        result = solve(problem, SearchLimits())
        self.assert_result(result, "solved", 3.0, 3, 4)
        self.assertEqual(result.actions, (D.DOWN, D.RIGHT, D.RIGHT))
        self.assertEqual(problem.goal_checks, ["S", "A", "B", "G"])
        self.assert_graph_replay(problem, result)

    def test_w2_cheaper_parent_replaces_discovered_path_and_skips_stale(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "A", 5), (D.DOWN, "B", 1)],
            "B": [(D.RIGHT, "A", 1)],
            "A": [(D.RIGHT, "G", 10)],
        })
        # The stale A:5 is popped after the third expansion, before G:12.
        result = solve(problem, SearchLimits(max_expanded_nodes=3))
        self.assert_result(result, "solved", 12.0, 3, 4)
        self.assertEqual(result.actions, (D.DOWN, D.RIGHT, D.RIGHT))
        self.assertEqual(problem.expansions, ["S", "B", "A"])
        self.assertEqual(problem.goal_checks, ["S", "B", "A", "G"])
        self.assert_graph_replay(problem, result)

    def test_equal_priorities_and_equal_cost_duplicate(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "A", 1), (D.DOWN, "B", 1)],
            "A": [(D.RIGHT, "G", 1)],
            "B": [(D.RIGHT, "G", 1)],
        })
        result = solve(problem, SearchLimits())
        self.assert_result(result, "solved", 2.0, 3, 4)
        # Check action-order tie breaking through expansions, not a forced solution.
        self.assertEqual(problem.expansions, ["S", "A", "B"])
        self.assert_graph_replay(problem, result)

    def test_invalid_successor_is_neither_counted_nor_costed(self):
        problem = _GraphProblem({
            "S": [(D.UP, None, None), (D.DOWN, "G", 2)],
        })
        result = solve(problem, SearchLimits())
        self.assert_result(result, "solved", 2.0, 1, 1)
        self.assertEqual(problem.cost_calls, [("S", D.DOWN, "G")])
        self.assert_graph_replay(problem, result)

    def test_only_stale_entries_remaining_are_not_expanded(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "A", 5), (D.DOWN, "B", 1)],
            "B": [(D.RIGHT, "A", 1)],
        })
        result = solve(problem, SearchLimits(max_expanded_nodes=3))
        self.assert_result(result, "unsolvable", None, 3, 3)
        self.assertEqual(problem.goal_checks, ["S", "B", "A"])

    def test_zero_node_limit_does_not_expand_initial(self):
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 1)]})
        result = solve(problem, SearchLimits(max_expanded_nodes=0))
        self.assert_result(result, "node_limit", None, 0, 0)
        self.assertEqual(problem.expansions, [])

    def test_node_limit_does_not_accept_a_discovered_expensive_goal(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "G", 9), (D.DOWN, "A", 1)],
            "A": [(D.RIGHT, "G", 1)],
        })
        result = solve(problem, SearchLimits(max_expanded_nodes=1))
        self.assert_result(result, "node_limit", None, 1, 2)

    def test_popped_goal_takes_precedence_over_node_limit(self):
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 1)]})
        result = solve(problem, SearchLimits(max_expanded_nodes=1))
        self.assert_result(result, "solved", 1.0, 1, 1)

    def test_exhausted_graph_at_exact_budget_is_unsolvable(self):
        result = solve(_GraphProblem({}), SearchLimits(max_expanded_nodes=1))
        self.assert_result(result, "unsolvable", None, 1, 0)

    def test_timeout_before_first_expansion_precedes_node_limit(self):
        with patch("search.ucs.perf_counter", side_effect=[0.0, 1.0]):
            result = solve(_GraphProblem({}), SearchLimits(1.0, 0))
        self.assert_result(result, "timeout", None, 0, 0)

    def test_initial_goal_takes_precedence_over_timeout(self):
        clock = _Clock()
        problem = _GraphProblem({}, initial="G")
        original_goal = problem.goal_test

        def delayed_goal(state):
            clock.now = 1.0
            return original_goal(state)

        with patch("search.ucs.perf_counter", clock), patch.object(
            problem, "goal_test", side_effect=delayed_goal
        ):
            result = solve(problem, SearchLimits(1.0, 0))
        self.assert_result(result, "solved", 0.0, 0, 0)

    def test_timeout_between_generated_successors_preserves_counters(self):
        clock = _Clock()
        problem = _GraphProblem({
            "S": [(D.RIGHT, "G", 9), (D.DOWN, "A", 1)],
        })
        original_result = problem.result

        def delayed_result(state, action):
            child = original_result(state, action)
            clock.now = 1.0
            return child

        with patch("search.ucs.perf_counter", clock), patch.object(
            problem, "result", side_effect=delayed_result
        ):
            result = solve(problem, SearchLimits(1.0))
        self.assert_result(result, "timeout", None, 1, 1)

    def test_timeout_before_first_successor_counts_started_expansion(self):
        clock = _Clock()
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 1)]})
        original_actions = problem.actions

        def delayed_actions(state):
            clock.now = 1.0
            return original_actions(state)

        with patch("search.ucs.perf_counter", clock), patch.object(
            problem, "actions", side_effect=delayed_actions
        ):
            result = solve(problem, SearchLimits(1.0))
        self.assert_result(result, "timeout", None, 1, 0)

    def test_popped_goal_takes_precedence_after_slow_final_transition(self):
        clock = _Clock()
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 1)]})
        original_result = problem.result

        def delayed_result(state, action):
            child = original_result(state, action)
            clock.now = 1.0
            return child

        with patch("search.ucs.perf_counter", clock), patch.object(
            problem, "result", side_effect=delayed_result
        ):
            result = solve(problem, SearchLimits(1.0))
        self.assert_result(result, "solved", 1.0, 1, 1)

    def test_timeout_after_final_invalid_successor_is_not_unsolvable(self):
        clock = _Clock()
        problem = _GraphProblem({"S": [(D.UP, None, None)]})
        original_result = problem.result

        def delayed_result(state, action):
            child = original_result(state, action)
            clock.now = 1.0
            return child

        with patch("search.ucs.perf_counter", clock), patch.object(
            problem, "result", side_effect=delayed_result
        ):
            result = solve(problem, SearchLimits(1.0))
        self.assert_result(result, "timeout", None, 1, 0)

    def test_invalid_step_costs_raise_instead_of_unsolvable(self):
        for cost in (0, -1, float("nan"), float("inf"), -float("inf")):
            with self.subTest(cost=cost):
                problem = _GraphProblem({"S": [(D.RIGHT, "G", cost)]})
                with self.assertRaisesRegex(ValueError, "positive and finite"):
                    solve(problem, SearchLimits())

    def test_accumulated_cost_overflow_raises(self):
        problem = _GraphProblem({
            "S": [(D.RIGHT, "A", 1e308)],
            "A": [(D.RIGHT, "G", 1e308)],
        })
        with self.assertRaisesRegex(ValueError, "Accumulated cost"):
            solve(problem, SearchLimits())

    def test_invalid_limits_are_rejected_on_direct_calls(self):
        with self.assertRaises(TypeError):
            solve(_GraphProblem({}), object())
        invalid = [SearchLimits(timeout_seconds=value)
                   for value in (0, -1, float("nan"), float("inf"))]
        invalid += [SearchLimits(max_expanded_nodes=value)
                    for value in (-1, 1.5, True)]
        for limits in invalid:
            with self.subTest(limits=limits), self.assertRaises(ValueError):
                solve(_GraphProblem({}), limits)

    def test_heuristic_is_ignored(self):
        heuristic = Mock(side_effect=AssertionError("UCS must ignore heuristic"))
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 1)]})
        result = solve(problem, SearchLimits(), heuristic)
        self.assert_result(result, "solved", 1.0, 1, 1)
        heuristic.assert_not_called()

    def test_solver_preserves_existing_external_memory_trace(self):
        self.assertFalse(tracemalloc.is_tracing())
        tracemalloc.start()
        try:
            result = solve(_GraphProblem({}), SearchLimits())
            self.assert_result(result, "unsolvable", None, 1, 0)
            self.assertTrue(tracemalloc.is_tracing())
        finally:
            tracemalloc.stop()


class UCSEngineTests(unittest.TestCase):
    def assert_engine_replay(self, problem, result):
        self.assertEqual(result.status, "solved")
        snapshot = problem.initial.copy()
        game = GameController(snapshot.board, snapshot.block)
        state, total_cost = problem.initial, 0.0
        for action in result.actions:
            child = problem.result(state, action)
            self.assertIsNotNone(child)
            total_cost += problem.step_cost(state, action, child)
            self.assertTrue(game.executeMove(action))
            self.assertEqual(child, State(game.board, game.block))
            state = child
        self.assertTrue(problem.goal_test(state))
        self.assertEqual(total_cost, result.total_cost)
        if result.actions:
            self.assertTrue(game.hasWon)
        return state

    def test_initial_engine_goal_has_empty_solution(self):
        problem = Problem(State(Board(1, 1, [[T.GOAL]]), Block(0, 0)))
        result = solve(problem, SearchLimits(max_expanded_nodes=0))
        self.assertEqual(result, SearchResult("solved", (), 0.0, 0, 0))
        self.assert_engine_replay(problem, result)

    def test_simple_corridor_exact_counters(self):
        board = Board(1, 4, [[T.NORMAL, T.NORMAL, T.NORMAL, T.GOAL]])
        problem = Problem(State(board, Block(0, 0)))
        result = solve(problem, SearchLimits())
        self.assertEqual(result, SearchResult(
            "solved", (D.RIGHT, D.RIGHT), 2.0, 2, 3
        ))
        self.assert_engine_replay(problem, result)

    def test_unsolvable_single_tile(self):
        problem = Problem(State(Board(1, 1), Block(0, 0)))
        self.assertEqual(solve(problem, SearchLimits()), SearchResult(
            "unsolvable", (), None, 1, 0
        ))

    def test_weighted_board_chooses_cost_over_length_and_replays(self):
        for unit_cost, expected_cost, expected_length in (
            (True, 4.0, 4), (False, 4.0 + 2 * FRAGILE_PENALTY, 4)
        ):
            with self.subTest(unit_cost=unit_cost):
                problem = _weighted_problem(unit_cost)
                before = deepcopy(problem.initial)
                initial_key = {problem.initial: "unchanged"}
                result = solve(problem, SearchLimits())
                self.assertEqual(result.total_cost, expected_cost)
                self.assertEqual(len(result.actions), expected_length)
                self.assert_engine_replay(problem, result)
                self.assertEqual(problem.initial, before)
                self.assertEqual(problem.initial.board.__dict__, before.board.__dict__)
                self.assertEqual(initial_key[problem.initial], "unchanged")

    def test_every_expanded_state_is_preserved(self):
        problem = _weighted_problem()
        observed = []
        original_result = problem.result

        def observe_result(state, action):
            observed.append((state, state.copy(), hash(state)))
            return original_result(state, action)

        with patch.object(problem, "result", side_effect=observe_result):
            result = solve(problem, SearchLimits())
        self.assertEqual(result.status, "solved")
        for state, before, original_hash in observed:
            self.assertEqual(state, before)
            self.assertEqual(state.board.__dict__, before.board.__dict__)
            self.assertEqual(hash(state), original_hash)

    def test_fragile_corridor_uses_shared_cost(self):
        board = Board(1, 4, [[T.NORMAL, T.FRAGILE, T.NORMAL, T.GOAL]])
        problem = Problem(State(board, Block(0, 0)))
        result = solve(problem, SearchLimits())
        self.assertEqual(result.total_cost, 2.0 + FRAGILE_PENALTY)
        self.assertEqual(len(result.actions), 2)
        self.assert_engine_replay(problem, result)

    def test_soft_switch_bridge_state_prevents_position_only_pruning(self):
        board = Board(1, 7, [[
            T.NORMAL, T.SOFT_SWITCH, T.NORMAL, T.BRIDGE,
            T.NORMAL, T.NORMAL, T.GOAL,
        ]])
        board.addBridge((0, 1), [(0, 3)])
        board.bridgeMap[(0, 1)] = {"nested": [1]}
        problem = Problem(State(board, Block(0, 0)))
        before = deepcopy(problem.initial)
        result = solve(problem, SearchLimits())
        self.assertEqual(result.total_cost, 6.0)
        self.assertEqual(len(result.actions), 6)
        final_state = self.assert_engine_replay(problem, result)
        self.assertTrue(final_state.board.bridgeState[(0, 1)])
        self.assertEqual(problem.initial.board.__dict__, before.board.__dict__)

    def test_heavy_switch_does_not_activate_when_lying(self):
        board = Board(1, 7, [[
            T.NORMAL, T.HEAVY_SWITCH, T.NORMAL, T.BRIDGE,
            T.NORMAL, T.NORMAL, T.GOAL,
        ]])
        board.addBridge((0, 1), [(0, 3)])
        problem = Problem(State(board, Block(0, 0)))
        result = solve(problem, SearchLimits())
        self.assertEqual(result.total_cost, 4.0)
        final_state = self.assert_engine_replay(problem, result)
        self.assertTrue(final_state.board.bridgeState[(0, 1)])

    def test_heavy_switch_activates_when_standing_with_fractional_cost(self):
        board = Board(1, 8, [[
            T.NORMAL, T.NORMAL, T.NORMAL, T.HEAVY_SWITCH,
            T.NORMAL, T.NORMAL, T.GOAL, T.BRIDGE,
        ]])
        board.addBridge((0, 3), [(0, 7)])
        problem = Problem(State(board, Block(0, 0)))
        result = solve(problem, SearchLimits())
        self.assertEqual(result.total_cost, 4.0)
        final_state = self.assert_engine_replay(problem, result)
        self.assertFalse(final_state.board.bridgeState[(0, 3)])

    def test_switch_removing_support_is_invalid(self):
        board = Board(1, 4, [[T.NORMAL, T.SOFT_SWITCH, T.BRIDGE, T.GOAL]])
        board.addBridge((0, 1), [(0, 2)])
        problem = Problem(State(board, Block(0, 0)))
        before = problem.initial.copy()
        self.assertEqual(solve(problem, SearchLimits()), SearchResult(
            "unsolvable", (), None, 1, 0
        ))
        self.assertEqual(problem.initial, before)

    def test_level_one_loaded_solution_replays(self):
        # This regression asserts the original two-move fixture, not campaign 1.
        path = Path(__file__).resolve().parents[1] / "tests/fixtures/legacy/level1.json"
        board, block = loadLevelFromJson(path, isDebug=False)
        problem = Problem(State(board, block).copy())
        result = solve(problem, SearchLimits())
        self.assertEqual(len(result.actions), 2)
        self.assertEqual(result.total_cost, 2.0)
        self.assert_engine_replay(problem, result)


class UCSRunnerTests(unittest.TestCase):
    def test_registry_and_runner_call_real_ucs(self):
        self.assertIs(get_solver(" UCS "), solve)
        result = run_search(_weighted_problem(), "ucs", SearchLimits())
        self.assertIsInstance(result, RunResult)
        self.assertEqual(result.search.status, "solved")
        self.assertEqual(result.search.total_cost, 4.0 + 2 * FRAGILE_PENALTY)
        self.assertEqual(len(result.search.actions), 4)
        self.assertGreaterEqual(result.search_time_seconds, 0.0)
        self.assertGreater(result.peak_memory_bytes, 0)
        self.assertFalse(tracemalloc.is_tracing())

    def test_runner_propagates_real_ucs_errors_and_cleans_up(self):
        problem = _GraphProblem({"S": [(D.RIGHT, "G", 0)]})
        with self.assertRaisesRegex(ValueError, "positive and finite"):
            run_search(problem, "ucs", SearchLimits())
        self.assertFalse(tracemalloc.is_tracing())
        # A new real call also verifies that the measurement lock was released.
        result = run_search(_GraphProblem({}), "ucs", SearchLimits())
        self.assertEqual(result.search.status, "unsolvable")

    def test_runner_preserves_all_real_ucs_statuses(self):
        cases = [
            (_GraphProblem({}, initial="G"), SearchLimits(), "solved"),
            (_GraphProblem({}), SearchLimits(), "unsolvable"),
            (_GraphProblem({}), SearchLimits(max_expanded_nodes=0), "node_limit"),
        ]
        for problem, limits, status in cases:
            with self.subTest(status=status):
                result = run_search(problem, "ucs", limits)
                self.assertEqual(result.search.status, status)
                self.assertFalse(tracemalloc.is_tracing())
        with patch("search.ucs.perf_counter", side_effect=[0.0, 1.0]):
            result = run_search(_GraphProblem({}), "ucs", SearchLimits(1.0))
        self.assertEqual(result.search.status, "timeout")
        self.assertEqual(result.search.actions, ())
        self.assertIsNone(result.search.total_cost)
        self.assertFalse(tracemalloc.is_tracing())


if __name__ == "__main__":
    unittest.main()
