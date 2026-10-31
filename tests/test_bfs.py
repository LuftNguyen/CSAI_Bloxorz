"""BFS contract tests. Run: python -m unittest discover -s tests -p test_bfs.py -v"""
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Block, Direction as D
from gameModel.board import Board, Tile as T, FRAGILE_PENALTY
from gameModel.problem import Problem
from gameModel.state import State
from search import bfs
from search.contracts import SearchLimits, SearchResult


class GraphProblem:
    """Ordered edges (action, destination, cost), using the public interface."""

    def __init__(self, edges, initial="S", goal="G"):
        self.initial = initial
        self.edges = edges
        self.goal = goal
        self.expansions = []

    def actions(self, state):
        self.expansions.append(state)
        if len(self.expansions) > 100:
            raise AssertionError("Repeated states were not pruned")
        return (action for action, _, _ in self.edges.get(state, ()))

    def result(self, state, action):
        return next(child for move, child, _ in self.edges[state] if move == action)

    def goal_test(self, state):
        return state == self.goal

    def step_cost(self, state, action, next_state):
        if next_state is None:
            raise AssertionError("Invalid moves must not be costed")
        return next(cost for move, _, cost in self.edges[state] if move == action)


class BfsContractTests(unittest.TestCase):
    def test_initial_goal_precedes_both_limits(self):
        with patch("search.bfs.perf_counter", side_effect=[0.0, 2.0]):
            result = bfs.solve(GraphProblem({}, initial="G"), SearchLimits(1.0, 0))
        self.assertEqual(result, SearchResult("solved", (), 0.0, 0, 0))

    def test_shortest_path_by_moves_even_when_more_expensive(self):
        problem = GraphProblem({
            "S": [(D.UP, "A", 1), (D.RIGHT, "G", 9)],
            "A": [(D.DOWN, "G", 1)],
        })
        result = bfs.solve(problem, SearchLimits())
        self.assertEqual(result, SearchResult("solved", (D.RIGHT,), 9.0, 2, 3))
        self.assertEqual(problem.expansions, ["S", "A"])

    def test_equal_length_paths_follow_action_order_and_sum_costs(self):
        problem = GraphProblem({
            "S": [(D.LEFT, "A", 2.5), (D.RIGHT, "B", 1)],
            "A": [(D.UP, "G", 3.25)],
            "B": [(D.DOWN, "G", 1)],
        })
        result = bfs.solve(problem, SearchLimits())
        self.assertEqual(result, SearchResult("solved", (D.LEFT, D.UP), 5.75, 3, 4))

    def test_cycles_self_loops_and_diamond_count_duplicates_before_filtering(self):
        problem = GraphProblem({
            "S": [(D.UP, "S", 1), (D.LEFT, "A", 1), (D.RIGHT, "B", 1)],
            "A": [(D.DOWN, "S", 1), (D.RIGHT, "C", 1)],
            "B": [(D.LEFT, "C", 1)],
        })
        result = bfs.solve(problem, SearchLimits())
        self.assertEqual(result, SearchResult("unsolvable", (), None, 4, 6))
        self.assertEqual(problem.expansions, ["S", "A", "B", "C"])

    def test_invalid_moves_do_not_count_as_generated(self):
        problem = GraphProblem({"S": [(D.UP, None, None), (D.RIGHT, "G", 2)]})
        self.assertEqual(bfs.solve(problem, SearchLimits()),
                         SearchResult("solved", (D.RIGHT,), 2.0, 1, 1))

    def test_dead_end_is_unsolvable(self):
        self.assertEqual(bfs.solve(GraphProblem({}), SearchLimits()),
                         SearchResult("unsolvable", (), None, 1, 0))

    def test_node_limit_before_expansion(self):
        problem = GraphProblem({"S": [(D.RIGHT, "A", 1)]})
        for limit in (0, 1):
            with self.subTest(limit=limit):
                result = bfs.solve(problem, SearchLimits(max_expanded_nodes=limit))
                self.assertEqual(result, SearchResult("node_limit", (), None, limit, limit))

    def test_dequeued_goal_precedes_node_limit(self):
        problem = GraphProblem({"S": [(D.RIGHT, "G", 1)]})
        result = bfs.solve(problem, SearchLimits(max_expanded_nodes=1))
        self.assertEqual(result, SearchResult("solved", (D.RIGHT,), 1.0, 1, 1))

    def test_goal_is_checked_on_dequeue_not_generation(self):
        problem = GraphProblem({"S": [(D.LEFT, "A", 1), (D.RIGHT, "G", 1)]})
        result = bfs.solve(problem, SearchLimits(max_expanded_nodes=1))
        self.assertEqual(result, SearchResult("node_limit", (), None, 1, 2))

    def test_timeout_before_expansion(self):
        with patch("search.bfs.perf_counter", side_effect=[0.0, 1.0]):
            result = bfs.solve(GraphProblem({}), SearchLimits(1.0))
        self.assertEqual(result, SearchResult("timeout", (), None, 0, 0))

    def test_timeout_during_successor_generation(self):
        problem = GraphProblem({"S": [(D.LEFT, "A", 1), (D.RIGHT, "G", 1)]})
        clock = Mock(return_value=0.0)
        original_result = problem.result

        def slow_result(state, action):
            clock.return_value = 1.0
            return original_result(state, action)

        with patch("search.bfs.perf_counter", clock), patch.object(
            problem, "result", side_effect=slow_result
        ):
            result = bfs.solve(problem, SearchLimits(1.0))
        self.assertEqual(result, SearchResult("timeout", (), None, 1, 1))

    def test_slow_final_transition_goal_and_exhaustion_boundaries(self):
        for child, status, cost, generated in (
            ("G", "solved", 1.0, 1),
            (None, "timeout", None, 0),
            ("S", "timeout", None, 1),
        ):
            with self.subTest(child=child):
                problem = GraphProblem({"S": [(D.RIGHT, child, 1)]})
                clock = Mock(return_value=0.0)

                def slow_result(state, action):
                    clock.return_value = 1.0
                    return child

                with patch("search.bfs.perf_counter", clock), patch.object(
                    problem, "result", side_effect=slow_result
                ):
                    result = bfs.solve(problem, SearchLimits(1.0))
                actions = (D.RIGHT,) if status == "solved" else ()
                self.assertEqual(result, SearchResult(status, actions, cost, 1, generated))

    def test_invalid_step_costs_raise(self):
        for cost in (0, -1, float("nan"), float("inf"), -float("inf")):
            with self.subTest(cost=cost):
                problem = GraphProblem({"S": [(D.RIGHT, "G", cost)]})
                with self.assertRaisesRegex(ValueError, "positive and finite"):
                    bfs.solve(problem, SearchLimits())

    def test_accumulated_cost_overflow_raises(self):
        problem = GraphProblem({
            "S": [(D.RIGHT, "A", 1e308)], "A": [(D.RIGHT, "G", 1e308)],
        })
        with self.assertRaisesRegex(ValueError, "Accumulated cost"):
            bfs.solve(problem, SearchLimits())

    def test_heuristic_is_ignored(self):
        heuristic = Mock(side_effect=AssertionError("BFS must ignore heuristic"))
        result = bfs.solve(GraphProblem({}, initial="G"), SearchLimits(), heuristic)
        self.assertEqual(result.status, "solved")
        heuristic.assert_not_called()


class BfsEngineTests(unittest.TestCase):
    def test_corridor_replay_cost_and_state_preservation(self):
        for tile, cost in ((T.NORMAL, 2.0), (T.FRAGILE, 2.0 + FRAGILE_PENALTY)):
            with self.subTest(tile=tile):
                board = Board(1, 4, [[T.NORMAL, tile, T.NORMAL, T.GOAL]])
                problem = Problem(State(board, Block(0, 0)))
                before = problem.initial.copy()
                initial_hash = hash(problem.initial)
                result = bfs.solve(problem, SearchLimits())
                self.assertEqual(result, SearchResult(
                    "solved", (D.RIGHT, D.RIGHT), cost, 2, 3
                ))
                state, replay_cost = problem.initial, 0.0
                for action in result.actions:
                    child = problem.result(state, action)
                    self.assertIsNotNone(child)
                    replay_cost += problem.step_cost(state, action, child)
                    state = child
                self.assertTrue(problem.goal_test(state))
                self.assertEqual(replay_cost, result.total_cost)
                self.assertEqual(problem.initial, before)
                self.assertEqual(problem.initial.board.__dict__, before.board.__dict__)
                self.assertEqual(hash(problem.initial), initial_hash)


if __name__ == "__main__":
    unittest.main()
