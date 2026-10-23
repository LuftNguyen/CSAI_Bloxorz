from math import isclose
from pathlib import Path

from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search
from search.contracts import SearchLimits
import sys


def main():
    level_number = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    level_path = (
        Path(__file__).resolve().parents[1]
        / "levels"
        / f"level{level_number}.json"
    )

    board, block = loadLevelFromJson(level_path, isDebug=False)
    problem = Problem(State(board, block).copy())
    initial_snapshot = problem.initial.copy()

    run = run_search(
        problem,
        "astar",
        SearchLimits(),
        heuristic=None,
    )
    result = run.search

    print("status:", result.status)
    print("actions:", [action.name for action in result.actions])
    print("cost:", result.total_cost)
    print("expanded:", result.expanded_nodes)
    print("generated:", result.generated_nodes)
    print("search time:", run.search_time_seconds)
    print("peak memory bytes:", run.peak_memory_bytes)

    assert result.status == "solved"
    assert problem.initial == initial_snapshot

    # Kiểm chứng ngoài khoảng đo của runner.
    state = problem.initial.copy()
    controller = GameController(board, block)
    replay_cost = 0.0

    for action in result.actions:
        child = problem.result(state, action)
        assert child is not None, f"Invalid action: {action}"

        replay_cost += problem.step_cost(state, action, child)

        assert controller.executeMove(action)
        assert child == State(controller.board, controller.block)

        state = child

    assert problem.goal_test(state)
    assert controller.hasWon
    assert isclose(
        replay_cost,
        result.total_cost,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )

    print("ASTAR GAME PASS")


if __name__ == "__main__":
    main()