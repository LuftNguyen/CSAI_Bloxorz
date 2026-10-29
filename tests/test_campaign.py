"""The ten playable stages must require their advertised mechanics."""
import unittest
import json

from gameModel.block import Orientation
from gameModel.gameController import GameController
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from levels.levelManager import LevelManager
from test_advanced_portfolio import ROOT, events, replay, solve


REQUIRED = {1: (), 2: (), 3: ('fragile',), 4: ('fragile',),
            5: ('bridge',), 6: ('bridge',), 7: ('bridge',),
            8: ('split', 'control', 'merge', 'fragile', 'bridge'),
            9: ('split', 'control', 'merge', 'bridge'),
            10: ('split', 'control', 'merge', 'bridge', 'fragile')}


class CampaignTests(unittest.TestCase):
    def test_similar_stage_pairs_have_different_floor_geometry(self):
        def footprint(number):
            data = json.loads((ROOT/f'levels/level{number}.json').read_text())
            return {(r, c) for r, row in enumerate(data['grid'])
                    for c, tile in enumerate(row) if tile != 'X'}
        def normalize(points):
            top, left = min(r for r, _ in points), min(c for _, c in points)
            return frozenset((r-top, c-left) for r, c in points)
        for left, right in [(1, 2), (8, 9)]:
            a, b = footprint(left), footprint(right)
            for swap in (False, True):
                for sr, sc in [(1,1), (-1,1), (1,-1), (-1,-1)]:
                    transformed = {(sr*(c if swap else r), sc*(r if swap else c))
                                   for r, c in b}
                    self.assertNotEqual(normalize(a), normalize(transformed))

    def test_declared_traps_have_real_effects_and_split_traps_are_dead_ends(self):
        from examples.audit_levels import replay_activation
        records = json.loads((ROOT/'levels/validation.json').read_text())['levels']
        total = 0
        for record in records:
            data = json.loads((ROOT/f'levels/level{record["level"]}.json').read_text())
            board, block = loadLevelFromJson(ROOT/f'levels/level{record["level"]}.json', False)
            initial = State(board, block).copy()
            for trap in data.get('design', {}).get('traps', []):
                with self.subTest(level=record['level'], trap=trap['position']):
                    witness = next(a for a in record['activations'] if a['position'] == trap['position'])
                    from gameModel.block import Direction
                    actions = tuple(Direction[a] for a in witness['actions'])
                    final = replay_activation(initial, tuple(trap['position']), actions)
                    if trap['kind'] in ('isolated_cubes', 'fatal_split'):
                        self.assertEqual(final.block.orientation, Orientation.SPLIT)
                        self.assertEqual(solve(final)[1].status, 'unsolvable')
                    else:
                        self.assertFalse(final.board.bridgeState[trap['bridge']])
                    if trap['kind'] in ('fatal_close', 'fatal_split'):
                        self.assertEqual(final.board.fatalSwitch, tuple(trap['position']))
                        self.assertEqual(solve(final)[1].status, 'unsolvable')
                    live = initial.copy()
                    controller = GameController(live.board, live.block)
                    for index, action in enumerate(actions):
                        fatal_last = trap['kind'] in ('fatal_close', 'fatal_split') and index == len(actions)-1
                        self.assertEqual(controller.executeMove(action), not fatal_last)
                    self.assertEqual(State(controller.board, controller.block), final)
                    controller.reset()
                    self.assertEqual(State(controller.board, controller.block), initial)
                    total += 1
        self.assertEqual(total, 17)

    def test_exactly_ten_playable_files_and_manager_limit(self):
        self.assertEqual(LevelManager().maxLevel, 10)
        self.assertEqual({p.name for p in (ROOT/'levels').glob('level[0-9]*.json')},
                         {f'level{n}.json' for n in REQUIRED})
        for number, minimum in {5: 5, 6: 5, 7: 7, 8: 2, 9: 5, 10: 7}.items():
            data = json.loads((ROOT/f'levels/level{number}.json').read_text())
            self.assertGreaterEqual(len(data['switches']), minimum)

    def test_every_advertised_mechanic_is_necessary_and_replays_live(self):
        for number, required in REQUIRED.items():
            with self.subTest(level=number):
                board, block = loadLevelFromJson(ROOT/f'levels/level{number}.json', False)
                initial = State(board, block).copy()
                before = initial.copy()
                problem, result = solve(initial)
                self.assertEqual(result.status, 'solved')
                self.assertGreaterEqual(len(result.actions), 10, 'Campaign regressed to a trivial route')
                self.assertGreaterEqual(result.expanded_nodes, 75)
                self.assertGreaterEqual(sum(t.name != 'VOID' for row in board.tiles for t in row), 45)
                self.assertGreaterEqual(board.rows, 9)
                self.assertGreaterEqual(board.cols, 11)
                self.assertGreaterEqual(len({a for a in result.actions if a.name != 'SWITCH'}), 2)
                observed, trace = replay(problem, result)
                self.assertTrue(set(required) <= observed)
                live = initial.copy()
                controller = GameController(live.board, live.block)
                for state, action, child in trace:
                    self.assertTrue(controller.executeMove(action))
                    self.assertEqual(State(controller.board, controller.block), child)
                    if 'fragile' in events(state, action, child):
                        self.assertNotEqual(child.block.orientation, Orientation.STANDING)
                self.assertTrue(controller.hasWon)
                controller.reset()
                self.assertEqual(State(controller.board, controller.block), initial)
                self.assertEqual(initial, before)
                for mechanic in required:
                    with self.subTest(disabled=mechanic):
                        self.assertEqual(solve(initial, (mechanic,))[1].status, 'unsolvable')
                for key, cells in initial.board.bridgeGroups.items():
                    with self.subTest(bridge=key):
                        self.assertFalse(initial.board.bridgeState[key])
                        self.assertEqual(solve(initial, ('bridge:'+key,))[1].status, 'unsolvable')
                        changes = [i for i, (s, a, c) in enumerate(trace)
                                   if s.board.bridgeState[key] != c.board.bridgeState[key]]
                        self.assertTrue(changes)
                        crossings = [i for i, (_, _, c) in enumerate(trace)
                                     if set(c.block.occupied()) & set(cells)]
                        self.assertTrue(crossings)
                        self.assertLessEqual(changes[0], crossings[0])
