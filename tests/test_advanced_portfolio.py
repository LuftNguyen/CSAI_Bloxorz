"""Behavioral fixtures; counterfactuals use copied metadata or filter real edges."""
import json
from pathlib import Path
import unittest

from gameModel.block import Direction as D, Orientation as O
from gameModel.problem import Problem
from gameModel.rules import pressed
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search.contracts import SearchLimits

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/advanced'
LIMITS = SearchLimits(timeout_seconds=10, max_expanded_nodes=100000)


def events(state, action, child):
    """Observe actual effects, including instantaneous split/teleport and merge."""
    found = set()
    if state.board.bridgeState != child.board.bridgeState:
        found.add('bridge')
    if state.block.orientation != O.SPLIT and child.block.orientation == O.SPLIT:
        found.add('split')
    if state.block.orientation == O.SPLIT and child.block.orientation != O.SPLIT:
        found.add('merge')
    if action == D.SWITCH:
        found.add('control')
    return found


class RestrictedProblem(Problem):
    """Test-only counterfactual; production transition implementation is reused.

    'bridge' removes switch effects on an isolated initial snapshot, preserving
    movement across switches and bridges' initial support.
    'split' rejects the atomic split/teleport; these cannot be isolated
    as independent mechanics in this engine. No source state is modified.
    """
    def __init__(self, initial, forbidden=()):
        snapshot = initial.copy()
        if 'bridge' in forbidden:
            snapshot.board.switchEffects = {}
        super().__init__(snapshot)
        self.forbidden = frozenset(forbidden)

    def result(self, state, action):
        child = super().result(state, action)
        if child is not None and events(state, action, child) & (self.forbidden - {'bridge'}):
            return None
        return child


def load(name):
    board, block = loadLevelFromJson(FIXTURES / (name + '.json'), False)
    return State(board, block).copy()


def solve(initial, forbidden=()):
    problem = RestrictedProblem(initial, forbidden)
    result = run_search(problem, 'astar', LIMITS, heuristic=None).search
    if result.status not in ('solved', 'unsolvable'):
        raise AssertionError(f'Inconclusive reachability: {result.status}')
    if result.status == 'solved':
        validate_solution(problem, result)
    return problem, result


def replay(problem, result):
    state = problem.initial.copy()
    observed = set()
    trace = []
    for action in result.actions:
        child = problem.result(state, action)
        if child is None:
            raise AssertionError('Illegal replay')
        observed |= events(state, action, child)
        trace.append((state, action, child))
        state = child
    return observed, trace


class AdvancedPortfolioTests(unittest.TestCase):
    def test_required_mechanics_full_solution_and_exhausted_restrictions(self):
        requirements = {
            'soft_gate': ('bridge',),
            'heavy_gate': ('bridge',),
            'split_control': ('split', 'control', 'merge'),
            'split_gate': ('split', 'control', 'bridge', 'merge'),
        }
        for name, required in requirements.items():
            with self.subTest(level=name):
                initial = load(name)
                before = initial.copy()
                problem, result = solve(initial)
                self.assertEqual(result.status, 'solved')
                observed, trace = replay(problem, result)
                self.assertTrue(set(required) <= observed)
                if name == 'split_gate':
                    first = {e: next(i for i, (s, a, c) in enumerate(trace)
                                     if e in events(s, a, c)) for e in required}
                    self.assertLess(first['split'], first['control'])
                    self.assertLess(first['control'], first['bridge'])
                    self.assertLess(first['bridge'], first['merge'])
                self.assertEqual(initial, before)
                for event in required:
                    with self.subTest(disabled=event):
                        _, restricted = solve(initial, (event,))
                        self.assertEqual(restricted.status, 'unsolvable')
                if 'bridge' in required:
                    self.assertTrue(initial.board.bridgeState)
                    self.assertFalse(any(initial.board.bridgeState.values()))
                    changes = [(s, a, c) for s, a, c in trace
                               if 'bridge' in events(s, a, c)]
                    self.assertTrue(changes)
                    for s, _, c in changes:
                        self.assertEqual(set(c.board.bridgeState), {'gate'})
                        self.assertTrue(c.board.bridgeState['gate'])
                        self.assertTrue(pressed(c) - pressed(s))
                    self.assertTrue(any(set(c.block.occupied()) & set(c.board.bridgeGroups['gate'])
                                        for _, _, c in trace))

    def test_optional_switch_is_not_mislabeled_required(self):
        initial = load('optional_gate')
        p, full = solve(initial)
        _, restricted = solve(initial, ('bridge',))
        self.assertEqual(full.status, 'solved')
        self.assertIn('bridge', replay(p, full)[0])
        self.assertEqual(restricted.status, 'solved')

    def test_reachable_open_bridge_is_insufficient_for_goal(self):
        initial = load('dead_gate')
        p, result = solve(initial)
        self.assertEqual(result.status, 'unsolvable')
        child = p.result(initial, D.RIGHT)
        self.assertIsNotNone(child)
        self.assertTrue(child.board.bridgeState['gate'])
        self.assertFalse(p.goal_test(child))
        self.assertEqual(solve(child)[1].status, 'unsolvable')

    def test_illegal_special_action_and_fall_preserve_source(self):
        initial = load('soft_gate')
        before = initial.copy()
        key = hash(initial)
        p = Problem(initial)
        self.assertIsNone(p.result(initial, D.SWITCH))
        self.assertIsNone(p.result(initial, D.UP))
        self.assertEqual(initial, before)
        self.assertEqual(hash(initial), key)

    def test_fixture_schema_start_and_goal(self):
        for path in sorted(FIXTURES.glob('*.json')):
            with self.subTest(level=path.stem):
                data = json.loads(path.read_text(encoding='utf-8'))
                initial = load(path.stem)
                self.assertEqual((initial.board.rows, initial.board.cols),
                                 (data['rows'], data['cols']))
                self.assertEqual(initial.block.orientation, O.STANDING)
                self.assertFalse(Problem(initial).goal_test(initial))


if __name__ == '__main__':
    unittest.main()
