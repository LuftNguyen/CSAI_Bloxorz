import unittest
from pathlib import Path

from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import validate_solution
from search.contracts import SearchLimits
from search.heuristics import HEURISTICS
from search.registry import get_solver

ROOT = Path(__file__).resolve().parents[1]
LIMITS = SearchLimits(timeout_seconds=60, max_expanded_nodes=1_000_000)


class LambdaSweepTests(unittest.TestCase):
    def test_astar_heuristics_match_ucs_cost_for_several_lambda(self):
        for lam in (0.0, 0.5, 2.0):
            for level in range(1, 11):
                costs = {}
                for name, algo, h in (("ucs", "ucs", None),
                                      ("manhattan", "astar", HEURISTICS["manhattan"]),
                                      ("relaxed", "astar", HEURISTICS["relaxed"]),
                                      ("relaxed_split", "astar", HEURISTICS["relaxed_split"])):
                    board, block = loadLevelFromJson(ROOT/f"levels/level{level}.json", False)
                    p = Problem(State(board, block).copy(), unit_cost=False, fragile_penalty=lam)
                    r = get_solver(algo)(p, LIMITS, h)
                    validate_solution(p, r)
                    costs[name] = round(r.total_cost, 9)
                with self.subTest(lam=lam, level=level):
                    self.assertEqual(len(set(costs.values())), 1, costs)