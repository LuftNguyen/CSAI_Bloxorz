"""Run the existing branch's A* with h=0, verify, then replay through controller.

This is an engine/solver integration check, not a benchmark or a new solver.
"""
import argparse
from pathlib import Path

from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search.contracts import SearchLimits


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('levels', type=int, nargs='*', default=[1,3,5,6,8,9,10])
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    for number in args.levels:
        board, block = loadLevelFromJson(root/f'levels/level{number}.json', False)
        p = Problem(State(board, block).copy())
        run = run_search(p, 'astar', SearchLimits(timeout_seconds=60, max_expanded_nodes=100000), heuristic=None)
        print(f'level={number} status={run.search.status} moves={len(run.search.actions)} cost={run.search.total_cost}')
        if run.search.status != 'solved':
            raise RuntimeError(f'Integration example did not solve level {number}: {run.search.status}')
        final = validate_solution(p, run.search)  # after timing and tracemalloc stop
        controller = GameController(board, block)
        state = p.initial
        for action in run.search.actions:
            state = p.result(state, action)
            assert controller.executeMove(action)
            assert state == State(controller.board, controller.block)
        assert state == final and controller.hasWon
        print('  actions:', ' '.join(a.name for a in run.search.actions))
        print('  verified goal/cost/controller parity; heuristic=0')


if __name__ == '__main__':
    main()
