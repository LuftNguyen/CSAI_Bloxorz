"""Heuristic checks. The exact optimal cost-to-go h* is computed here by brute force
(full reachable state space + reverse Dijkstra) and is used ONLY as a test oracle;
it is not a team solver."""

import unittest
from collections import defaultdict, deque
from heapq import heappop, heappush
from itertools import count
from math import isfinite
from pathlib import Path

from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Board, Tile as T
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from search import heuristics as H

ROOT = Path(__file__).resolve().parents[1]
LEVELS = sorted((ROOT / "levels").glob("level*.json"), key=lambda p: int(p.stem[5:]))
STATE_CAP = 50_000


def make_problem(tiles, start, unit_cost=False, bridges=()):
    rows, cols = len(tiles), len(tiles[0])
    cmap = {"X": T.VOID, ".": T.NORMAL, "F": T.FRAGILE, "G": T.GOAL,
            "w": T.SOFT_SWITCH, "W": T.HEAVY_SWITCH, "B": T.BRIDGE}
    board = Board(rows, cols, [[cmap[ch] for ch in row] for row in tiles])
    for switch, cells in bridges:
        board.addBridge(switch, cells)
    return Problem(State(board, Block(*start)), unit_cost=unit_cost)


def explore(problem):
    """All reachable states, edges (s -> s', cost) and exact h* for each."""
    index, states, edges = {problem.initial: 0}, [problem.initial], defaultdict(list)
    reverse = defaultdict(list)
    queue = deque([0])
    while queue:
        i = queue.popleft()
        s = states[i]
        if problem.goal_test(s):
            continue
        for a in problem.actions(s):
            child = problem.result(s, a)
            if child is None:
                continue
            j = index.get(child)
            if j is None:
                j = index[child] = len(states)
                states.append(child)
                queue.append(j)
                assert len(states) <= STATE_CAP, "state space too large for test"
            cost = problem.step_cost(s, a, child)
            edges[i].append((j, cost))
            reverse[j].append((i, cost))
    star, heap, tie = {}, [], count()
    for i, s in enumerate(states):
        if problem.goal_test(s):
            star[i] = 0.0
            heappush(heap, (0.0, next(tie), i))
    while heap:
        d, _, j = heappop(heap)
        if d > star.get(j, float("inf")):
            continue
        for i, cost in reverse[j]:
            if d + cost < star.get(i, float("inf")):
                star[i] = d + cost
                heappush(heap, (d + cost, next(tie), i))
    return states, edges, star


def check_heuristic(test, problem, heuristic, name, explored=None):
    states, edges, star = explored if explored is not None else explore(problem)
    values = [heuristic(problem, s) for s in states]
    for i, s in enumerate(states):
        h = values[i]
        test.assertTrue(isfinite(h) and h >= 0, f"{name}: bad value {h} at {s}")
        if problem.goal_test(s):
            test.assertEqual(h, 0.0, f"{name}: h(goal) != 0")
        if i in star:  # admissible wherever the goal is still reachable
            test.assertLessEqual(h, star[i] + 1e-9, f"{name}: overestimates at {s.block}")
        for j, cost in edges[i]:  # consistency on every real edge
            test.assertLessEqual(h, cost + values[j] + 1e-9, f"{name}: inconsistent {s.block}")
    return states, star, values


class SmallBoardTests(unittest.TestCase):
    def test_straight_corridor_values(self):
        problem = make_problem(["...G."], (0, 0))
        # (0,0) stand -> RIGHT lie(0,1-2) -> RIGHT stand(0,3): goal. 2 moves.
        self.assertEqual(H.relaxed_distance(problem, problem.initial), 2.0)
        goal = State(problem.initial.board, Block(0, 3))
        self.assertEqual(H.relaxed_distance(problem, goal), 0.0)
        self.assertEqual(H.manhattan_lower_bound(problem, goal), 0.0)

    def test_lying_on_goal_is_not_zero(self):
        problem = make_problem(["...G."], (0, 0))
        lying = State(problem.initial.board, Block(0, 3, 0, 1, O.LYING))
        self.assertGreater(H.relaxed_distance(problem, lying), 0)
        self.assertGreater(H.manhattan_lower_bound(problem, lying), 0)

    def test_fragile_standing_is_respected(self):
        problem = make_problem([".F.G"], (0, 0))
        # Lying across the fragile cell is fine: RIGHT (lie on 1-2), RIGHT (stand on 3).
        self.assertEqual(H.relaxed_distance(problem, problem.initial), 6.0)  # fragile 5 + goal 1
        # Standing on a fragile tile is never legal, so such a block is a dead end.
        standing_on_fragile = State(problem.initial.board, Block(0, 1))
        self.assertEqual(H.relaxed_distance(problem, standing_on_fragile), H.DEAD_H)

    def test_unreachable_goal_is_finite_sentinel(self):
        problem = make_problem([".X.G"], (0, 0))
        h = H.relaxed_distance(problem, problem.initial)
        self.assertEqual(h, H.DEAD_H)
        self.assertTrue(isfinite(h))

    def test_bridge_cells_are_optimistically_open(self):
        # Bridge cell (0,2) is closed in the real game after toggling; relaxed treats it as open.
        problem = make_problem(["..w.G"], (0, 1), bridges=[((0, 2), [(0, 3)])])
        self.assertLess(H.relaxed_distance(problem, problem.initial), H.DEAD_H)

    def test_zero_heuristic(self):
        problem = make_problem(["..G"], (0, 0))
        self.assertEqual(H.zero(problem, problem.initial), 0.0)

    def test_unsupported_state_falls_back_to_zero(self):
        class Split:
            pass
        problem = make_problem(["..G"], (0, 0))
        self.assertEqual(H.relaxed_distance(problem, Split()), 0.0)
        self.assertEqual(H.manhattan_lower_bound(problem, Split()), 0.0)

    def test_state_is_not_modified(self):
        problem = make_problem(["..w.G"], (0, 1), bridges=[((0, 2), [(0, 3)])])
        before = problem.initial.copy()
        H.relaxed_distance(problem, problem.initial)
        H.manhattan_lower_bound(problem, problem.initial)
        self.assertEqual(problem.initial, before)

    def test_manhattan_is_loose_where_cost_is_high(self):
        # Relaxed distance must dominate (>=) the closed-form bound.
        problem = make_problem(["...F...", "...F..G", "......."], (0, 0))
        s = problem.initial
        self.assertGreaterEqual(H.relaxed_distance(problem, s), H.manhattan_lower_bound(problem, s))

    def test_admissible_on_hand_made_boards(self):
        boards = [
            (["...G."], (0, 0)),
            (["....", ".F..", "...G"], (0, 0)),
            (["w...", ".XX.", "..BG"], (0, 0)),
        ]
        for tiles, start in boards:
            for unit in (False, True):
                problem = make_problem(tiles, start, unit)
                for name, h in H.HEURISTICS.items():
                    with self.subTest(board=tiles, unit=unit, h=name):
                        check_heuristic(self, problem, h, name)


class LevelTests(unittest.TestCase):
    def test_all_levels_admissible_and_consistent(self):
        for path in LEVELS:
            for unit in (False, True):
                board, block = loadLevelFromJson(path, isDebug=False)
                problem = Problem(State(board, block).copy(), unit_cost=unit)
                explored = explore(problem) 
                for name, h in H.HEURISTICS.items():
                    with self.subTest(level=path.stem, unit_cost=unit, heuristic=name):
                        check_heuristic(self, problem, h, name, explored)

    def test_relaxed_never_worse_than_manhattan_at_start(self):
        for path in LEVELS:
            board, block = loadLevelFromJson(path, isDebug=False)
            problem = Problem(State(board, block).copy())
            with self.subTest(level=path.stem):
                self.assertGreaterEqual(
                    H.relaxed_distance(problem, problem.initial),
                    H.manhattan_lower_bound(problem, problem.initial),
                )

class SplitTests(unittest.TestCase):
    def _level(self, n, unit_cost=True):
        board, block = loadLevelFromJson(ROOT / "levels" / f"level{n}.json", isDebug=False)
        return Problem(State(board, block).copy(), unit_cost=unit_cost)

    def test_split_state_returns_zero(self):
        problem = self._level(8)
        split = State(problem.initial.board, Block.split([(7, 2), (7, 12)]))
        self.assertEqual(H.relaxed_distance(problem, split), 0.0)
        self.assertEqual(H.manhattan_lower_bound(problem, split), 0.0)

    def test_split_switch_is_zero_target(self):
        problem = self._level(8)
        board = problem.initial.board
        for (r, c) in board.splitTargets:
            state = State(board, Block(r, c))
            self.assertEqual(H.relaxed_distance(problem, state), 0.0)
            self.assertEqual(H.manhattan_lower_bound(problem, state), 0.0)

    def test_start_is_not_dead_on_split_levels(self):
        for n in (8, 9, 10):
            problem = self._level(n)
            self.assertLess(H.relaxed_distance(problem, problem.initial), H.DEAD_H)

    def test_roll_graph_ignores_switch_action(self):
        # _build_table must not call resultingState(SWITCH) on a non-split block.
        H.precompute(self._level(8))
        
if __name__ == "__main__":
    unittest.main()
