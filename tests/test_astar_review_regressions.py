"""Contract regressions for A*, with UCS running the same fixtures as a control.

A* is expected to fail both cases until its production implementation is fixed.
The clock advances inside result(); no wall-clock sleeps are needed.
"""
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Direction
from search import astar, ucs
from search.contracts import SearchLimits, SearchResult


class _GraphProblem:
    """Minimal shared Problem interface; states are immutable string keys."""

    def __init__(self, edges):
        self.initial = "S"
        self.edges = edges

    def actions(self, state):
        return [action for action, _, _ in self.edges.get(state, ())]

    def result(self, state, action):
        for candidate, child, _ in self.edges.get(state, ()):
            if candidate == action:
                return child
        raise AssertionError("Action was not supplied by actions()")

    def goal_test(self, state):
        return state == "G"

    def step_cost(self, state, action, next_state):
        for candidate, child, cost in self.edges.get(state, ()):
            if candidate == action and child == next_state:
                return cost
        raise AssertionError("Cost requested for an invalid transition")


class _RegressionCases:
    def test_timeout_after_final_invalid_successor(self):
        # CONTRACT sections 7-8: an expired search must report timeout.
        problem = _GraphProblem({"S": [(Direction.UP, None, None)]})
        clock = Mock(return_value=0.0)
        original_result = problem.result

        def delayed_result(state, action):
            child = original_result(state, action)
            clock.return_value = 2.0  # Last engine call exceeds the 1s budget.
            return child

        with patch(self.clock_target, clock), patch.object(
            problem, "result", side_effect=delayed_result
        ) as result_mock, patch.object(
            problem, "step_cost", wraps=problem.step_cost
        ) as cost_mock:
            result = self.solver(problem, SearchLimits(timeout_seconds=1.0))

        result_mock.assert_called_once_with("S", Direction.UP)
        cost_mock.assert_not_called()
        self.assertEqual(result.status, "timeout", f"Actual result: {result!r}")
        self.assertEqual(result, SearchResult("timeout", (), None, 1, 0))

    def test_accumulated_cost_overflow_raises(self):
        # Both steps are positive and finite; their float sum is not finite.
        # CONTRACT section 7: data/numeric errors must not become unsolvable.
        problem = _GraphProblem({
            "S": [(Direction.RIGHT, "A", 1e308)],
            "A": [(Direction.RIGHT, "G", 1e308)],
        })
        with self.assertRaisesRegex(ValueError, "Accumulated cost.*finite"):
            result = self.solver(problem, SearchLimits())
            self.fail(
                "Expected ValueError for accumulated cost overflow; "
                f"actual result: {result!r}"
            )


class AStarRegressionTests(_RegressionCases, unittest.TestCase):
    solver = staticmethod(astar.solve)
    clock_target = "search.astar.perf_counter"


class UCSControlTests(_RegressionCases, unittest.TestCase):
    solver = staticmethod(ucs.solve)
    clock_target = "search.ucs.perf_counter"


if __name__ == "__main__":
    unittest.main()
