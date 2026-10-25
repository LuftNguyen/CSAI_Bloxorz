"""Replay checked data witnesses; no search execution or algorithm test changes."""
import json
from pathlib import Path
import unittest

from examples.audit_levels import ActivationProblem, data_hash, replay_activation
from gameModel.block import Direction
from gameModel.board import Tile
from gameModel.gameController import GameController
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import validate_solution
from search.contracts import SearchResult

ROOT = Path(__file__).resolve().parents[1]


def search_result(record):
    return SearchResult('solved', tuple(Direction[a] for a in record['actions']),
                        record['total_cost'], 0, 0)


class CompletedLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT/'levels/validation.json').read_text(encoding='utf-8'))['levels']

    def test_manifest_matches_all_current_levels(self):
        self.assertEqual([r['level'] for r in self.records], list(range(1, 15)))
        for record in self.records:
            with self.subTest(level=record['level']):
                data = json.loads((ROOT/f'levels/level{record["level"]}.json').read_text(encoding='utf-8'))
                self.assertEqual(data['level_id'], record['level'])
                self.assertEqual(data_hash(data), record['data_sha256'],
                                 'Level changed: rerun python -m examples.audit_levels --write')

    def test_no_decorative_switch_or_uncontrolled_bridge(self):
        for number in range(1, 15):
            with self.subTest(level=number):
                board, _ = loadLevelFromJson(ROOT/f'levels/level{number}.json', False)
                bridge_cells = {p for cells in board.bridgeGroups.values() for p in cells}
                controlled = {key for effects in board.switchEffects.values() for key, _ in effects}
                self.assertEqual(controlled, set(board.bridgeGroups))
                for r, row in enumerate(board.initialTiles):
                    for c, tile in enumerate(row):
                        if tile in (Tile.SOFT_SWITCH, Tile.HEAVY_SWITCH):
                            self.assertTrue(board.switchEffects.get((r, c)), (number, r, c))
                        if tile == Tile.SPLIT_SWITCH:
                            self.assertIn((r, c), board.splitTargets)
                        if tile == Tile.BRIDGE:
                            self.assertIn((r, c), bridge_cells)

    def test_all_stage_solutions_replay_and_reset(self):
        for record in self.records:
            with self.subTest(level=record['level']):
                board, block = loadLevelFromJson(ROOT/f'levels/level{record["level"]}.json', False)
                initial = State(board, block).copy()
                p = Problem(initial)
                result = search_result(record['solution'])
                final = validate_solution(p, result)
                controller = GameController(board, block)
                state = initial
                for action in result.actions:
                    state = p.result(state, action)
                    self.assertTrue(controller.executeMove(action))
                    self.assertEqual(state, State(controller.board, controller.block))
                self.assertEqual(state, final)
                self.assertTrue(controller.hasWon)
                controller.reset()
                self.assertEqual(State(controller.board, controller.block), initial)

    def test_every_switch_has_reachable_effect_witness(self):
        total = 0
        for record in self.records:
            board, block = loadLevelFromJson(ROOT/f'levels/level{record["level"]}.json', False)
            initial = State(board, block).copy()
            expected = set(board.switchEffects) | set(board.splitTargets)
            self.assertEqual({tuple(a['position']) for a in record['activations']}, expected)
            for activation in record['activations']:
                target = tuple(activation['position'])
                with self.subTest(level=record['level'], switch=target):
                    result = search_result(activation)
                    validate_solution(ActivationProblem(initial.copy(), target), result)
                    replay_activation(initial, target, result.actions)
                    self.assertEqual(initial, State(board, block))
                    total += 1
        self.assertGreaterEqual(total, 24)
