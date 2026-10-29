import unittest
from unittest.mock import patch

from gameModel.block import Direction
from search.astar import solve
from search.contracts import SearchLimits


class SmallProblem:
    def __init__(self, edges=None, initial="S"):
        self.initial = initial
        self.edges = edges if edges is not None else {
            "S": [
                (Direction.UP, "A", 5.0),
                (Direction.RIGHT, "B", 1.0),
            ],
            "B": [(Direction.UP, "A", 1.0)],
            "A": [(Direction.RIGHT, "G", 1.0)],
            "G": [],
        }

    def actions(self, state):
        return [action for action, _, _ in self.edges[state]]

    def result(self, state, action):
        for candidate, child, _ in self.edges[state]:
            if candidate == action:
                return child
        return None

    def goal_test(self, state):
        return state == "G"

    def step_cost(self, state, action, next_state):
        for candidate, child, cost in self.edges[state]:
            if candidate == action and child == next_state:
                return cost
        raise ValueError("Invalid transition")


class AStarTests(unittest.TestCase):
    def assert_failure(self, result, status, expanded, generated):
        self.assertEqual(result.status, status)
        self.assertEqual(result.actions, ())
        self.assertIsNone(result.total_cost)
        self.assertEqual(result.expanded_nodes, expanded)
        self.assertEqual(result.generated_nodes, generated)

    def test_cheaper_path(self):
        result = solve(SmallProblem(), SearchLimits())

        self.assertEqual(result.status, "solved")
        self.assertEqual(
            result.actions,
            (Direction.RIGHT, Direction.UP, Direction.RIGHT),
        )
        self.assertEqual(result.total_cost, 3.0)
        self.assertEqual(result.expanded_nodes, 3)
        self.assertEqual(result.generated_nodes, 4)

    def test_reopening(self):
        problem = SmallProblem(edges={
            "S": [
                (Direction.UP, "A", 3.0),
                (Direction.RIGHT, "B", 1.0),
            ],
            "B": [(Direction.UP, "A", 1.0)],
            "A": [(Direction.RIGHT, "G", 3.0)],
            "G": [],
        })
        estimates = {"S": 0.0, "A": 0.0, "B": 4.0, "G": 0.0}

        result = solve(
            problem,
            SearchLimits(),
            heuristic=lambda problem, state: estimates[state],
        )

        self.assertEqual(result.status, "solved")
        self.assertEqual(
            result.actions,
            (Direction.RIGHT, Direction.UP, Direction.RIGHT),
        )
        self.assertEqual(result.total_cost, 5.0)
        self.assertEqual(result.expanded_nodes, 4)
        self.assertEqual(result.generated_nodes, 5)

    def test_stale_entry_and_unsolvable(self):
        problem = SmallProblem(edges={
            "S": [
                (Direction.UP, "A", 5.0),
                (Direction.RIGHT, "B", 1.0),
            ],
            "B": [(Direction.UP, "A", 1.0)],
            "A": [],
            "G": [],
        })

        result = solve(problem, SearchLimits())

        self.assert_failure(result, "unsolvable", 3, 3)

    def test_node_limit(self):
        for limit, expanded, generated in (
            (0, 0, 0),
            (1, 1, 2),
        ):
            with self.subTest(limit=limit):
                result = solve(
                    SmallProblem(),
                    SearchLimits(
                        timeout_seconds=60.0,
                        max_expanded_nodes=limit,
                    ),
                )

                self.assert_failure(
                    result, "node_limit", expanded, generated
                )

    def test_timeout(self):
        with patch(
            "search.astar.perf_counter",
            side_effect=[0.0, 2.0],
        ):
            result = solve(
                SmallProblem(),
                SearchLimits(
                    timeout_seconds=1.0,
                    max_expanded_nodes=100,
                ),
            )

        self.assert_failure(result, "timeout", 0, 0)

    def test_initial_goal(self):
        result = solve(
            SmallProblem(initial="G"),
            SearchLimits(max_expanded_nodes=0),
        )

        self.assertEqual(result.status, "solved")
        self.assertEqual(result.actions, ())
        self.assertEqual(result.total_cost, 0.0)
        self.assertEqual(result.expanded_nodes, 0)
        self.assertEqual(result.generated_nodes, 0)

    def test_cycle(self):
        problem = SmallProblem(edges={
            "S": [(Direction.RIGHT, "A", 1.0)],
            "A": [
                (Direction.LEFT, "S", 1.0),
                (Direction.RIGHT, "G", 1.0),
            ],
            "G": [],
        })

        result = solve(problem, SearchLimits())

        self.assertEqual(result.status, "solved")
        self.assertEqual(
            result.actions,
            (Direction.RIGHT, Direction.RIGHT),
        )
        self.assertEqual(result.total_cost, 2.0)
        self.assertEqual(result.expanded_nodes, 2)
        self.assertEqual(result.generated_nodes, 3)

    def test_invalid_heuristic(self):
        for value in (-1.0, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solve(
                        SmallProblem(),
                        SearchLimits(),
                        heuristic=lambda problem, state: value,
                    )


if __name__ == "__main__":
    unittest.main()