"""Integration acceptance only; member algorithms are imported unchanged."""
from pathlib import Path
import unittest

from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search import bfs, dfs, ucs, astar, heuristics
from search.contracts import SearchLimits

ROOT = Path(__file__).resolve().parents[1]


class SolverIntegrationTests(unittest.TestCase):
    def problem(self, number):
        board, block = loadLevelFromJson(ROOT/f'levels/level{number}.json',False)
        return Problem(State(board,block).copy())

    def test_all_member_solvers_replay_all_campaign_stages(self):
        for number in range(1,11):
            problem = self.problem(number)
            snapshot = problem.initial.copy()
            costs = {}
            for name, module in (('bfs',bfs),('dfs',dfs),('ucs',ucs),('astar',astar)):
                with self.subTest(level=number,algorithm=name):
                    result = module.solve(problem,SearchLimits(timeout_seconds=30),None)
                    self.assertEqual(result.status,'solved')
                    validate_solution(problem,result)
                    self.assertEqual(problem.initial,snapshot)
                    costs[name] = result.total_cost
            if 'ucs' in costs and 'astar' in costs:
                self.assertEqual(costs['ucs'],costs['astar'])

    def test_astar_with_heuristics_matches_ucs_cost_on_split_levels(self):
        for number in (8,9):
            problem = self.problem(number)
            optimal = run_search(problem,'ucs',SearchLimits(timeout_seconds=60)).search
            self.assertEqual(optimal.status,'solved')
            for heuristic in (heuristics.manhattan_lower_bound,heuristics.relaxed_distance):
                with self.subTest(level=number,heuristic=heuristic.__name__):
                    result = run_search(problem,'astar',SearchLimits(timeout_seconds=60),heuristic).search
                    self.assertEqual(result.status,'solved')
                    validate_solution(problem,result)
                    self.assertEqual(result.total_cost,optimal.total_cost)

    def test_runner_accepts_the_member_zero_on_split(self):
        problem = self.problem(8)
        result = run_search(problem,'astar',SearchLimits(timeout_seconds=30),heuristics.zero)
        self.assertEqual(result.search.status,'solved')
        validate_solution(problem,result.search)
