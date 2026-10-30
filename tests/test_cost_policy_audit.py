"""Independent cost-policy edge checks; no edits to member solvers or heuristics."""
from collections import deque
import unittest

from examples.audit_cost_models import policy, reference_cost
from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Board, Tile as T, TILE_COST
from gameModel.problem import Problem
from gameModel.state import State
from search import ucs
from search.contracts import SearchLimits


class CostPolicyAuditTests(unittest.TestCase):
    def test_ucs_matches_exhaustive_bellman_ford_reference(self):
        board = Board(3,4,[[T.NORMAL,T.FRAGILE,T.NORMAL,T.GOAL],
                           [T.NORMAL]*4,[T.NORMAL]*4])
        for model in ('current','upstream_weights_extended','unit'):
            with self.subTest(model=model), policy(model) as unit:
                p = Problem(State(board,Block(0,0)),unit_cost=unit)
                states,seen,edges = [p.initial],{p.initial:0},[]
                for state in states:
                    for action in p.actions(state):
                        child = p.result(state,action)
                        if child is None:
                            continue
                        if child not in seen:
                            seen[child] = len(states)
                            states.append(child)
                        edges.append((seen[state],seen[child],
                                      reference_cost(state,action,child,unit=unit)))
                # Independent full-graph relaxation, not the heap/frontier solver.
                best = [float('inf')]*len(states)
                best[0] = 0
                for _ in range(len(states)-1):
                    changed = False
                    for source,target,cost in edges:
                        candidate = best[source]+cost
                        if candidate < best[target]:
                            best[target] = candidate
                            changed = True
                    if not changed:
                        break
                exact = min(best[i] for i,s in enumerate(states) if p.goal_test(s))
                result = ucs.solve(p,SearchLimits())
                self.assertEqual(result.status,'solved')
                self.assertEqual(result.total_cost,exact)
                self.assertEqual(exact,2 if unit else 5)

    def test_policy_restores_globals_even_after_exception(self):
        original = dict(TILE_COST)
        with self.assertRaisesRegex(RuntimeError,'intentional'):
            with policy('upstream_weights_extended'):
                self.assertEqual(TILE_COST[T.FRAGILE],5)
                raise RuntimeError('intentional')
        self.assertEqual(TILE_COST,original)

    def test_max_does_not_sum_tiles_or_reward_mixed_switch(self):
        board = Board(3,7)
        board.setTile(1,1,T.SOFT_SWITCH)
        p = Problem(State(board,Block(1,0)))
        child = p.result(p.initial,D.RIGHT)
        self.assertEqual(p.step_cost(p.initial,D.RIGHT,child),1)
        board.setTile(1,2,T.SOFT_SWITCH)
        p = Problem(State(board,Block(1,0)))
        child = p.result(p.initial,D.RIGHT)
        self.assertEqual(p.step_cost(p.initial,D.RIGHT,child),.75)

    def test_split_move_charges_only_active_cube_and_switch_is_one(self):
        board = Board(3,8)
        board.setTile(1,6,T.FRAGILE)
        p = Problem(State(board,Block.split(((1,0),(1,6)))))
        moved = p.result(p.initial,D.RIGHT)
        self.assertEqual(p.step_cost(p.initial,D.RIGHT,moved),1)
        switched = p.result(p.initial,D.SWITCH)
        self.assertEqual(p.step_cost(p.initial,D.SWITCH,switched),1)

    def test_teleport_charges_destinations_not_split_pad(self):
        board = Board(3,10)
        board.setTile(0,3,T.SPLIT_SWITCH)
        board.splitTargets[(0,3)] = ((1,5),(1,8))
        board.setTile(1,8,T.FRAGILE)
        p = Problem(State(board,Block(0,1,0,1,O.LYING)))
        child = p.result(p.initial,D.RIGHT)
        self.assertIsNotNone(child)
        self.assertEqual(child.block.orientation,O.SPLIT)
        self.assertEqual(p.step_cost(p.initial,D.RIGHT,child),4)
        self.assertEqual(Problem(p.initial,unit_cost=True).step_cost(p.initial,D.RIGHT,child),1)

    def test_every_reachable_small_board_edge_matches_oracle(self):
        board = Board(3,7)
        board.setTile(0,1,T.FRAGILE)
        board.setTile(1,2,T.SOFT_SWITCH)
        board.setTile(2,3,T.HEAVY_SWITCH)
        board.setTile(0,3,T.SPLIT_SWITCH)
        board.splitTargets[(0,3)] = ((1,4),(2,6))
        initial = State(board,Block(0,0))
        for model in ('current','upstream_weights_extended','unit'):
            with self.subTest(model=model), policy(model) as unit:
                p = Problem(initial.copy(),unit_cost=unit)
                queue,seen = deque([p.initial]),{p.initial}
                edges = 0
                while queue:
                    state = queue.popleft()
                    snapshot = state.copy()
                    for action in p.actions(state):
                        child = p.result(state,action)
                        if child is None:
                            continue
                        edges += 1
                        actual = p.step_cost(state,action,child)
                        self.assertEqual(actual,reference_cost(state,action,child,unit=unit))
                        self.assertGreaterEqual(actual,1 if unit else min(TILE_COST.values()))
                        self.assertLessEqual(actual,1 if unit else max(TILE_COST.values()))
                        if child not in seen:
                            seen.add(child)
                            queue.append(child)
                    self.assertEqual(state,snapshot)
                self.assertGreater(edges,100)
                self.assertLess(len(seen),5000)
