from search.astar import solve
from search.contracts import SearchLimits
from gameModel.block import Direction
from unittest.mock import patch

class SmallProblem:
    initial = "S"

    edges = {
        "S": [
            (Direction.UP, "A", 5.0),
            (Direction.RIGHT, "B", 1.0),
        ],
        "B": [
            (Direction.UP, "A", 1.0),
        ],
        "A": [
            (Direction.RIGHT, "G", 1.0),
        ],
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


if __name__ == "__main__":
    result = solve(SmallProblem(), SearchLimits())

    print("status:", result.status)
    print("actions:", [action.name for action in result.actions])
    print("cost:", result.total_cost)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "solved"
    assert result.actions == (
        Direction.RIGHT,
        Direction.UP,
        Direction.RIGHT,
    )
    assert result.total_cost == 3.0
    assert result.expanded_nodes == 3
    assert result.generated_nodes == 4

    print("PASS")

    print("\n--- Test reopening ---")

    reopening_problem = SmallProblem()
    reopening_problem.edges = {
        "S": [
            (Direction.UP, "A", 3.0),
            (Direction.RIGHT, "B", 1.0),
        ],
        "B": [
            (Direction.UP, "A", 1.0),
        ],
        "A": [
            (Direction.RIGHT, "G", 3.0),
        ],
        "G": [],
    }

    estimates = {
        "S": 0.0,
        "A": 0.0,
        "B": 4.0,
        "G": 0.0,
    }

    def test_heuristic(problem, state):
        return estimates[state]

    result = solve(
        reopening_problem,
        SearchLimits(),
        heuristic=test_heuristic,
    )

    print("status:", result.status)
    print("actions:", [action.name for action in result.actions])
    print("cost:", result.total_cost)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "solved"
    assert result.actions == (
        Direction.RIGHT,
        Direction.UP,
        Direction.RIGHT,
    )
    assert result.total_cost == 5.0
    assert result.expanded_nodes == 4
    assert result.generated_nodes == 5

    print("REOPENING PASS")

    print("\n--- Test stale entry and unsolvable ---")

    stale_problem = SmallProblem()
    stale_problem.edges = {
        "S": [
            (Direction.UP, "A", 5.0),
            (Direction.RIGHT, "B", 1.0),
        ],
        "B": [
            (Direction.UP, "A", 1.0),
        ],
        "A": [],
        "G": [],
    }

    result = solve(stale_problem, SearchLimits())

    print("status:", result.status)
    print("actions:", result.actions)
    print("cost:", result.total_cost)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "unsolvable"
    assert result.actions == ()
    assert result.total_cost is None
    assert result.expanded_nodes == 3
    assert result.generated_nodes == 3

    print("STALE ENTRY AND UNSOLVABLE PASS")

    print("\n--- Test node limit ---")

    result = solve(
        SmallProblem(),
        SearchLimits(
            timeout_seconds=60.0,
            max_expanded_nodes=0,
        ),
    )

    print("status:", result.status)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "node_limit"
    assert result.actions == ()
    assert result.total_cost is None
    assert result.expanded_nodes == 0
    assert result.generated_nodes == 0

    result = solve(
        SmallProblem(),
        SearchLimits(
            timeout_seconds=60.0,
            max_expanded_nodes=1,
        ),
    )

    print("status:", result.status)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "node_limit"
    assert result.actions == ()
    assert result.total_cost is None
    assert result.expanded_nodes == 1
    assert result.generated_nodes == 2

    print("NODE LIMIT PASS")

    print("\n--- Test timeout ---")

    # Lần đầu ghi mốc 0; lần kiểm tra kế tiếp đã là 2 giây.
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

    print("status:", result.status)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "timeout"
    assert result.actions == ()
    assert result.total_cost is None
    assert result.expanded_nodes == 0
    assert result.generated_nodes == 0

    print("TIMEOUT PASS")

    print("\n--- Test initial goal ---")

    initial_goal_problem = SmallProblem()
    initial_goal_problem.initial = "G"

    result = solve(
        initial_goal_problem,
        SearchLimits(
            timeout_seconds=60.0,
            max_expanded_nodes=0,
        ),
    )

    print("status:", result.status)
    print("actions:", result.actions)
    print("cost:", result.total_cost)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "solved"
    assert result.actions == ()
    assert result.total_cost == 0.0
    assert result.expanded_nodes == 0
    assert result.generated_nodes == 0

    print("INITIAL GOAL PASS")

    print("\n--- Test cycle ---")

    cycle_problem = SmallProblem()
    cycle_problem.edges = {
        "S": [
            (Direction.RIGHT, "A", 1.0),
        ],
        "A": [
            (Direction.LEFT, "S", 1.0),
            (Direction.RIGHT, "G", 1.0),
        ],
        "G": [],
    }

    result = solve(cycle_problem, SearchLimits())

    print("status:", result.status)
    print("actions:", [action.name for action in result.actions])
    print("cost:", result.total_cost)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)

    assert result.status == "solved"
    assert result.actions == (
        Direction.RIGHT,
        Direction.RIGHT,
    )
    assert result.total_cost == 2.0
    assert result.expanded_nodes == 2
    assert result.generated_nodes == 3

    print("CYCLE PASS")

    print("\n--- Test invalid heuristic ---")

    for invalid_value in (-1.0, float("nan"), float("inf")):

        def invalid_heuristic(problem, state):
            return invalid_value

        try:
            solve(
                SmallProblem(),
                SearchLimits(),
                heuristic=invalid_heuristic,
            )
        except ValueError as error:
            print(f"Rejected {invalid_value}: {error}")
        else:
            raise AssertionError(
                f"Expected ValueError for heuristic={invalid_value}"
            )

    print("INVALID HEURISTIC PASS")