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
from gameModel.rules import pressed, winning, transition
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import validate_solution
from search.contracts import SearchLimits
from search.registry import get_solver

ROOT = Path(__file__).resolve().parents[1]


def data_hash(data):
    return sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class ActivationProblem(Problem):
    """A data-audit goal: activate a specific switch, not finish the stage."""
    def __init__(self, initial, target):
        super().__init__(initial)
        self.target = target

    def goal_test(self, state):
        if state.board.fatalSwitch is not None:
            return state.board.fatalSwitch == self.target
        if self.target in state.board.splitTargets:
            return (state.block.orientation == Orientation.SPLIT and
                    state.block.cubes == state.board.splitTargets[self.target])
        return self.target in pressed(state)

    def result(self, state, action):
        # A witness must not continue moving after the real stage is already won.
        if winning(state):
            return None
        child, valid, _ = transition(state, action)
        if not valid:
            # This audit goal is to demonstrate a trap, not win the stage.
            return child if child.board.fatalSwitch == self.target else None
        # CLOSE/OPEN can be reached while already in the requested state. Such
        # a no-op is not an activation witness; keep searching for a real effect.
        if child is not None and self.target in pressed(child) - pressed(state):
            effects = state.board.switchEffects.get(self.target, ())
            if effects and not any(state.board.bridgeState[key] != child.board.bridgeState[key]
                                   for key, _ in effects):
                return None
        return child


def replay_activation(initial, target, actions):
    """Check actual effects and live-controller parity, not just JSON metadata."""
    state = initial.copy()
    live = initial.copy()
    controller = GameController(live.board, live.block)
    changed = False
    for index, action in enumerate(actions):
        if winning(state):
            raise ValueError('Activation witness continues after victory')
        child, valid, lost = transition(state, action)
        terminal_witness = (lost and child.board.fatalSwitch == target and index == len(actions)-1)
        if (not valid and not terminal_witness) or controller.executeMove(action) != valid:
            raise ValueError('Activation witness contains an illegal move')
        if child != State(controller.board, controller.block):
            raise ValueError('Controller differs from search transition')
        changed |= terminal_witness
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
    limits = SearchLimits(timeout_seconds=60, max_expanded_nodes=100000)
    count = 0
    for number in range(1, 11):
        path = ROOT/f'levels/level{number}.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        board, block = loadLevelFromJson(path, False)
        initial = State(board, block).copy()
        problem = Problem(initial)
        # This script proves correctness, not performance. Use the same
        # registered solver without repeated tracemalloc overhead.
        result = get_solver('astar')(problem, limits, heuristic=None)
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
            # Correctness witness queries need no repeated memory profiling.
            activation = get_solver('astar')(probe, limits, heuristic=None)
            if activation.status != 'solved':
                raise ValueError(f'Level {number}, switch {target}: {activation.status}')
            validate_solution(probe, activation)
            replay_activation(initial, target, activation.actions)
            record['activations'].append({'position': list(target), **proof(activation),
                                          'outcome': 'loss' if target in board.fatalCloseSwitches | board.fatalSplitSwitches else 'effect'})
            count += 1
        report['levels'].append(record)
        print(f'level={number}: solved moves={len(result.actions)} cost={result.total_cost}; '
              f'{len(record["activations"])} switches verified', flush=True)
    if args.write:
        (ROOT/'levels/validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(f'PASS: 10 stage solutions, {count} switch activation witnesses; h=0')


if __name__ == '__main__':
    main()
