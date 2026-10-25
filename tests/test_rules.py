"""Engine/loader/integration tests. No search algorithm implementation tests."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Board, Tile as T
from gameModel.state import State
from gameModel.problem import Problem
from gameModel.gameController import GameController
from levels.levelLoader import loadLevelFromJson, _load
from runner import validate_solution, run_search
from search.contracts import SearchResult, SearchLimits

ROOT = Path(__file__).resolve().parents[1]


def problem(block=None):
    return Problem(State(Board(7, 9), block or Block(3, 1)))


class RuleTests(unittest.TestCase):
    def test_fragile_break_reset_and_block_hash(self):
        data = {'rows': 3, 'cols': 9, 'start': {'r':1,'c':1},
                'grid': ['XXXXXXXXX', 'XS..F..GX', 'XXXXXXXXX']}
        board, block = _load(data)
        game = GameController(board, block)
        self.assertTrue(game.executeMove(D.RIGHT))
        self.assertFalse(game.executeMove(D.RIGHT))
        self.assertEqual(board.getTile(1,4), T.VOID)
        game.reset()
        self.assertEqual(board.getTile(1,4), T.FRAGILE)
        self.assertFalse(game.isGameOver)
        for b in [Block(1,1), Block(1,1,0,1,O.LYING), Block.split(((1,1),(1,5)),1)]:
            with self.subTest(block=b):
                self.assertEqual(b, b.copy())
                self.assertEqual(hash(b), hash(b.copy()))

    def test_fragile_full_lying_standing_and_cube(self):
        p = problem()
        p.initial.board.setTile(3, 2, T.FRAGILE)
        child = p.result(p.initial, D.RIGHT)
        self.assertIsNotNone(child)
        self.assertEqual(child.board.getTile(3, 2), T.FRAGILE)
        state = State(p.initial.board, Block(3, 3, 0, 1, O.LYING))
        self.assertIsNone(p.result(state, D.LEFT))  # standing at c=2
        game = GameController(state.board, state.block)
        self.assertFalse(game.executeMove(D.LEFT))
        self.assertEqual(game.board.getTile(3, 2), T.VOID)
        self.assertTrue(game.isGameOver)
        p = problem(Block.split(((3, 1), (5, 6))))
        p.initial.board.setTile(3, 2, T.FRAGILE)
        self.assertEqual(p.result(p.initial, D.RIGHT).board.getTile(3, 2), T.FRAGILE)

    def test_soft_heavy_and_fixed_effect_modes(self):
        for tile in (T.SOFT_SWITCH, T.HEAVY_SWITCH):
            for mode, initial, expected in [('TOGGLE', False, True), ('TOGGLE', True, False),
                                            ('OPEN', True, True), ('OPEN', False, True),
                                            ('CLOSE', True, False), ('CLOSE', False, False)]:
                with self.subTest(tile=tile, mode=mode, initial=initial):
                    p = problem(Block(3, 1, 0, 1, O.LYING))
                    b = p.initial.board
                    b.setTile(3, 3, tile)
                    b.addBridgeGroup('a', [(0, 0)], initial)
                    b.switchEffects[(3, 3)] = (('a', mode),)
                    child = p.result(p.initial, D.RIGHT)
                    self.assertEqual(child.board.bridgeState['a'], expected)
        p = problem()
        p.initial.board.setTile(3, 2, T.HEAVY_SWITCH)
        p.initial.board.addBridgeGroup('a', [(0, 0)], False)
        p.initial.board.switchEffects[(3, 2)] = (('a', 'OPEN'),)
        self.assertFalse(p.result(p.initial, D.RIGHT).board.bridgeState['a'])

    def test_multiple_bridges_shared_state_and_ordered_effects(self):
        p = problem()
        b = p.initial.board
        b.addBridgeGroup('a', [(0, 0)], True)
        b.addBridgeGroup('b', [(0, 1)], False)
        b.setTile(3, 2, T.SOFT_SWITCH)
        b.setTile(3, 3, T.SOFT_SWITCH)
        # Insert opposite order: processing is still sorted by switch position.
        b.switchEffects[(3, 3)] = (('a', 'CLOSE'),)
        b.switchEffects[(3, 2)] = (('a', 'OPEN'), ('b', 'TOGGLE'))
        child = p.result(p.initial, D.RIGHT)
        self.assertEqual(child.board.bridgeState, {'a': False, 'b': True})
        self.assertEqual(b.bridgeState, {'a': True, 'b': False})

    def test_bridge_closes_under_inactive_cube(self):
        p = problem(Block.split(((3, 1), (5, 6))))
        b = p.initial.board
        b.addBridgeGroup('a', [(5, 6)], True)
        b.setTile(3, 2, T.SOFT_SWITCH)
        b.switchEffects[(3, 2)] = (('a', 'CLOSE'),)
        self.assertIsNone(p.result(p.initial, D.RIGHT))
        game = GameController(b, p.initial.block)
        self.assertFalse(game.executeMove(D.RIGHT))
        self.assertTrue(game.isGameOver)

    def test_no_reactivation_on_switch_or_continued_occupancy(self):
        p = problem(Block.split(((3, 1), (5, 6))))
        b = p.initial.board
        b.setTile(3, 1, T.SOFT_SWITCH)
        b.addBridgeGroup('a', [(0, 0)], True)
        b.switchEffects[(3, 1)] = (('a', 'TOGGLE'),)
        child = p.result(p.initial, D.SWITCH)
        self.assertEqual(child.board.bridgeState, b.bridgeState)
        child = p.result(child, D.LEFT)
        self.assertTrue(child.board.bridgeState['a'])
        child = p.result(child, D.SWITCH)
        child = p.result(child, D.RIGHT)
        child = p.result(child, D.LEFT)
        self.assertFalse(child.board.bridgeState['a'])  # leaves, then re-enters

    def test_split_teleport_and_control_identity(self):
        p = problem(Block(3, 1, 0, 1, O.LYING))
        b = p.initial.board
        b.setTile(3, 3, T.SPLIT_SWITCH)
        b.splitTargets[(3, 3)] = ((1, 1), (1, 6))
        child = p.result(p.initial, D.RIGHT)
        self.assertEqual(child.block.cubes, ((1, 1), (1, 6)))
        self.assertEqual(child.block.orientation, O.SPLIT)
        self.assertNotIn(D.SWITCH, p.actions(p.initial))
        self.assertIn(D.SWITCH, p.actions(child))
        switched = p.result(child, D.SWITCH)
        self.assertNotEqual(child, switched)
        self.assertEqual(switched.block.cubes, child.block.cubes)
        self.assertEqual(switched.board.tiles, child.board.tiles)
        self.assertEqual(switched.board.bridgeState, child.board.bridgeState)
        copied = switched.copy()
        self.assertEqual(copied, switched)
        self.assertEqual(hash(copied), hash(switched))
        moved = p.result(switched, D.LEFT)
        self.assertEqual(moved.block.cubes, ((1, 1), (1, 5)))
        self.assertEqual(child.block.cubes, ((1, 1), (1, 6)))

    def test_cube_cannot_win_or_press_heavy_or_split(self):
        for tile in (T.GOAL, T.HEAVY_SWITCH, T.SPLIT_SWITCH):
            with self.subTest(tile=tile):
                p = problem(Block.split(((3, 1), (5, 6))))
                b = p.initial.board
                b.setTile(3, 2, tile)
                b.addBridgeGroup('a', [(0, 0)], False)
                b.switchEffects[(3, 2)] = (('a', 'OPEN'),)
                b.splitTargets[(3, 2)] = ((1, 1), (1, 6))
                child = p.result(p.initial, D.RIGHT)
                self.assertFalse(p.goal_test(child))
                self.assertFalse(child.board.bridgeState['a'])
                self.assertEqual(child.block.cubes, ((3, 2), (5, 6)))

    def test_split_requires_standing(self):
        p = problem()
        b = p.initial.board
        b.setTile(3, 2, T.SPLIT_SWITCH)
        b.splitTargets[(3, 2)] = ((1, 1), (1, 6))
        self.assertEqual(p.result(p.initial, D.RIGHT).block.orientation, O.LYING)

    def test_teleport_cannot_chain_or_press_heavy_and_adjacent_rejoin(self):
        for tile in (T.HEAVY_SWITCH, T.SPLIT_SWITCH):
            with self.subTest(tile=tile):
                p = problem(Block(3,1,0,1,O.LYING))
                b = p.initial.board
                b.setTile(3,3,T.SPLIT_SWITCH)
                b.splitTargets[(3,3)] = ((1,1),(1,6))
                b.setTile(1,1,tile)
                b.splitTargets[(1,1)] = ((4,1),(4,6))
                b.addBridgeGroup('a',[(0,0)],False)
                b.switchEffects[(1,1)] = (('a','OPEN'),)
                child = p.result(p.initial,D.RIGHT)
                self.assertEqual(child.block.cubes, ((1,1),(1,6)))
                self.assertFalse(child.board.bridgeState['a'])
        b.splitTargets[(3,3)] = ((1,1),(1,2))
        child = p.result(p.initial,D.RIGHT)
        self.assertEqual(child.block, Block(1,1,0,1,O.LYING))

    def test_teleport_special_destinations_and_invalid_support(self):
        p = problem(Block(3, 1, 0, 1, O.LYING))
        b = p.initial.board
        b.setTile(3, 3, T.SPLIT_SWITCH)
        b.splitTargets[(3, 3)] = ((1, 1), (1, 6))
        b.setTile(1, 1, T.FRAGILE)
        b.setTile(1, 6, T.SOFT_SWITCH)
        b.addBridgeGroup('a', [(0, 0)], False)
        b.switchEffects[(1, 6)] = (('a', 'OPEN'),)
        self.assertTrue(p.result(p.initial, D.RIGHT).board.bridgeState['a'])
        for tile in (T.VOID,):
            b.setTile(1, 1, tile)
            self.assertIsNone(p.result(p.initial, D.RIGHT))
        b.splitTargets[(3, 3)] = ((-1, 1), (1, 6))
        self.assertIsNone(p.result(p.initial, D.RIGHT))

    def test_rejoin_both_axes_overlap_and_bounds(self):
        for positions, action, expected in [(((3, 1), (3, 3)), D.RIGHT, Block(3, 2, 0, 1, O.LYING)),
                                             (((1, 3), (3, 3)), D.DOWN, Block(2, 3, 1, 0, O.LYING))]:
            with self.subTest(positions=positions):
                p = problem(Block.split(positions))
                self.assertEqual(p.result(p.initial, action).block, expected)
        p = problem(Block.split(((3, 1), (3, 2))))
        self.assertIsNone(p.result(p.initial, D.RIGHT))
        p = problem(Block.split(((0, 1), (5, 6))))
        self.assertIsNone(p.result(p.initial, D.UP))
        invalid = State(p.initial.board, Block.split(((-1,1),(5,6))))
        self.assertIsNone(p.result(invalid, D.SWITCH))
        self.assertIsNone(problem().result(problem().initial, D.SWITCH))

    def test_deepcopy_sibling_keys_and_static_rule_metadata(self):
        p = problem(Block.split(((3, 1), (5, 6))))
        p.initial.board.addBridgeGroup('a', [(0, 0)], False)
        p.initial.board.setTile(3, 2, T.SOFT_SWITCH)
        p.initial.board.switchEffects[(3, 2)] = (('a', 'TOGGLE'),)
        before = p.initial.copy()
        first = p.result(p.initial, D.RIGHT)
        snapshot = first.copy()
        second = p.result(p.initial, D.DOWN)
        second.board.bridgeGroups['a'].append((0, 1))
        self.assertEqual(first, snapshot)
        self.assertEqual(p.initial, before)
        self.assertEqual(hash(p.initial), hash(before))
        changed = p.initial.copy()
        changed.board.switchEffects[(3, 2)] = (('a', 'OPEN'),)
        self.assertNotEqual(changed, p.initial)

    def test_get_tile_all_boundaries(self):
        b = Board(2, 3)
        for position in [(-1,0),(0,-1),(2,0),(0,3),(100,100)]:
            with self.subTest(position=position):
                self.assertEqual(b.getTile(*position), T.VOID)
        self.assertEqual(b.getTile(1, 2), T.NORMAL)

    def test_split_controller_parity_reset_and_switch_cost(self):
        board, block = loadLevelFromJson(ROOT/'levels/level12.json', False)
        p = Problem(State(board, block).copy())
        controller = GameController(board, block)
        state = p.initial
        # Explicit SWITCH fixture; switching never changes positions or bridges.
        sequence = [D.RIGHT,D.RIGHT,D.SWITCH,D.SWITCH,D.RIGHT,D.RIGHT,D.RIGHT,D.RIGHT,D.RIGHT]
        for action in sequence:
            child = p.result(state, action)
            self.assertIsNotNone(child)
            self.assertTrue(controller.executeMove(action))
            self.assertEqual(child, State(controller.board, controller.block))
            if action == D.SWITCH:
                self.assertEqual(p.step_cost(state, action, child), 1.0)
            state = child
        self.assertTrue(p.goal_test(state))
        controller.reset()
        self.assertEqual(State(controller.board, controller.block), p.initial)


class LoaderAndReplayTests(unittest.TestCase):
    def test_all_levels_and_legacy_shared_bridge_fix(self):
        for number in range(1, 15):
            with self.subTest(level=number):
                b, _ = loadLevelFromJson(ROOT/f'levels/level{number}.json', False)
                self.assertEqual(len(b.tiles), b.rows)
        raw = json.loads((ROOT/'levels/level5.json').read_text())
        self.assertEqual(raw['grid'][6][14], 'W')
        self.assertEqual(raw['grid'][6][15], '.')
        b, _ = loadLevelFromJson(ROOT/'levels/level5.json', False)
        self.assertEqual(b.switchEffects[(5,5)][0][0], b.switchEffects[(6,14)][0][0])
        self.assertEqual(len(b.bridgeState), 1)

    def test_initial_closed_and_repeated_reset(self):
        b, block = loadLevelFromJson(ROOT/'levels/level13.json', False)
        initial = State(b, block).copy()
        self.assertFalse(b.bridgeState['crossing'])
        self.assertEqual(b.getTile(2, 4), T.VOID)
        for _ in range(2):
            b.applySwitch((1,2))
            self.assertEqual(b.getTile(2,4), T.BRIDGE)
            b.reset()
            self.assertEqual(State(b,block), initial)

    def test_loader_rejects_invalid_data(self):
        valid = json.loads((ROOT/'levels/level14.json').read_text())
        invalid = []
        def case(change):
            data = deepcopy(valid)
            change(data)
            invalid.append(data)
        case(lambda d: d.update(rows=0))
        case(lambda d: d['grid'].__setitem__(0, '?XXXXXXXXX'))
        case(lambda d: d['grid'].__setitem__(0, 'X'))
        case(lambda d: d['grid'].__setitem__(0, 'GXXXXXXXXX'))
        case(lambda d: d['start'].update(c=-1))
        case(lambda d: d['start'].update(c=0))
        case(lambda d: d['bridges'][0].update(initial_open='false'))
        case(lambda d: d['bridges'][1].update(id='a'))
        case(lambda d: d['bridges'][0].update(tiles=[[99,0]]))
        case(lambda d: d['bridges'][0].update(tiles=[[2,4],[2,4]]))
        case(lambda d: d['bridges'][1].update(tiles=[[2,4]]))
        case(lambda d: d['switches'][0]['effects'][0].update(bridge='missing'))
        case(lambda d: d['switches'][0]['effects'][0].update(mode='INVALID'))
        case(lambda d: d['switches'][0].update(position=[0,0]))
        case(lambda d: d.update(schema_version=3))
        for index, data in enumerate(invalid):
            with self.subTest(case=index), self.assertRaises(ValueError):
                _load(data)
        split = json.loads((ROOT/'levels/level12.json').read_text())
        for targets in [[], [[1,1],[1,1]], [[1,1],[99,99]]]:
            with self.subTest(targets=targets), self.assertRaises(ValueError):
                split['splits'][0]['targets'] = targets
                _load(split)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'bad.json'
            path.write_text('{bad', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Invalid level'):
                loadLevelFromJson(path, False)

    def test_verified_solution_and_rejection(self):
        b, block = loadLevelFromJson(ROOT/'levels/level1.json', False)
        p = Problem(State(b, block))
        initial = p.initial.copy()
        solved = SearchResult('solved', (D.RIGHT,D.RIGHT), 2.0+1e-11, 0, 0)
        self.assertTrue(p.goal_test(validate_solution(p, solved)))
        self.assertEqual(p.initial, initial)
        for actions, cost in [((D.LEFT,),1), ((D.RIGHT,),1), ((D.RIGHT,D.RIGHT),3), ((D.SWITCH,),1), (('RIGHT',),1)]:
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                validate_solution(p, SearchResult('solved', actions, cost, 0, 0))

    def test_unverified_split_heuristic_guard(self):
        b, block = loadLevelFromJson(ROOT/'levels/level12.json', False)
        with self.assertRaisesRegex(ValueError, 'unverified'):
            run_search(Problem(State(b,block)), 'astar', SearchLimits(), lambda p,s: 1)
