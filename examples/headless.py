"""Engine wiring and a fixed replay fixture, without any search implementation."""
from pathlib import Path
from gameModel.block import Direction
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search
from search.contracts import SearchLimits


def main():
    board, block = loadLevelFromJson(Path(__file__).resolve().parents[1] / "levels/level1.json", isDebug=False)
    problem = Problem(State(board, block).copy())
    print("initial:", problem.initial)
    print("actions:", [a.name for a in problem.actions(problem.initial)])
    for action in problem.actions(problem.initial):
        child = problem.result(problem.initial, action)
        print(action.name, child, "cost:", None if child is None else problem.step_cost(problem.initial, action, child))
    state = problem.initial
    controller = GameController(board, block)
    cost = 0.0
    # A fixed two-move fixture verified against the Stage 1 geometry.
    for action in (Direction.RIGHT, Direction.RIGHT):
        child = problem.result(state, action)
        assert child is not None
        cost += problem.step_cost(state, action, child)
        assert controller.executeMove(action)
        assert child == State(controller.board, controller.block)
        state = child
    assert problem.goal_test(state) and controller.hasWon
    print(f"replay: RIGHT RIGHT; goal=True; cost={cost}")
    try:
        run_search(problem, "bfs", SearchLimits())
    except NotImplementedError as exc:
        print("team solver:", exc)


if __name__ == "__main__":
    main()
