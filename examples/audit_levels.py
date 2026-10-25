"""Data validation using the existing A*, never a new search implementation.

Writes replay witnesses only with --write. Metrics are not benchmark results.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from gameModel.block import Direction, Orientation
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.rules import pressed, winning
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search.contracts import SearchLimits

ROOT = Path(__file__).resolve().parents[1]


def data_hash(data):
    return sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class ActivationProblem(Problem):
    """A data-audit goal: activate a specific switch, not finish the stage."""
    def __init__(self, initial, target):
        super().__init__(initial)
        self.target = target

    def goal_test(self, state):
        if self.target in state.board.splitTargets:
            return (state.block.orientation == Orientation.SPLIT and
                    state.block.cubes == state.board.splitTargets[self.target])
        return self.target in pressed(state)

    def result(self, state, action):
        # A witness must not continue moving after the real stage is already won.
        return None if winning(state) else super().result(state, action)


def replay_activation(initial, target, actions):
    """Check actual effects and live-controller parity, not just JSON metadata."""
    state = initial.copy()
    live = initial.copy()
    controller = GameController(live.board, live.block)
    problem = Problem(initial)
    changed = False
    for action in actions:
        if winning(state):
            raise ValueError('Activation witness continues after victory')
        child = problem.result(state, action)
        if child is None or not controller.executeMove(action):
            raise ValueError('Activation witness contains an illegal move')
        if child != State(controller.board, controller.block):
            raise ValueError('Controller differs from search transition')
        if target in pressed(child) - pressed(state):
            changed |= any(state.board.bridgeState[key] != child.board.bridgeState[key]
                           for key, _ in state.board.switchEffects.get(target, ()))
        if target in state.board.splitTargets and action != Direction.SWITCH:
            landing = state.block.resultingState(action)
            if landing.orientation == Orientation.STANDING and (landing.r, landing.c) == target:
                changed |= child.block != landing
        state = child
    if not changed:
        raise ValueError(f'Switch {target} witness has no actual bridge/split effect')
    return state


def proof(result):
    return {'actions': [a.name for a in result.actions], 'total_cost': result.total_cost}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true', help='refresh levels/validation.json')
    args = parser.parse_args()
    report = {'format_version': 1, 'method': 'existing A* with h=0; correctness audit, not benchmark', 'levels': []}
    limits = SearchLimits(timeout_seconds=10, max_expanded_nodes=100000)
    count = 0
    for number in range(1, 15):
        path = ROOT/f'levels/level{number}.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        board, block = loadLevelFromJson(path, False)
        initial = State(board, block).copy()
        problem = Problem(initial)
        result = run_search(problem, 'astar', limits, heuristic=None).search
        if result.status != 'solved':
            raise ValueError(f'Level {number}: {result.status}')
        final = validate_solution(problem, result)
        live = initial.copy()
        controller = GameController(live.board, live.block)
        for action in result.actions:
            if not controller.executeMove(action):
                raise ValueError('Stage solution cannot replay in controller')
        if not controller.hasWon or final != State(controller.board, controller.block):
            raise ValueError('Stage solution controller mismatch')
        record = {'level': number, 'data_sha256': data_hash(data), 'solution': proof(result), 'activations': []}
        for target in sorted(set(board.switchEffects) | set(board.splitTargets)):
            probe = ActivationProblem(initial.copy(), target)
            activation = run_search(probe, 'astar', limits, heuristic=None).search
            if activation.status != 'solved':
                raise ValueError(f'Level {number}, switch {target}: {activation.status}')
            validate_solution(probe, activation)
            replay_activation(initial, target, activation.actions)
            record['activations'].append({'position': list(target), **proof(activation)})
            count += 1
        report['levels'].append(record)
        print(f'level={number}: solved moves={len(result.actions)} cost={result.total_cost}; '
              f'{len(record["activations"])} switches verified', flush=True)
    if args.write:
        (ROOT/'levels/validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(f'PASS: 14 stage solutions, {count} switch activation witnesses; h=0')


if __name__ == '__main__':
    main()
