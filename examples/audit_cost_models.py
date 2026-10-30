"""Cost-policy sensitivity audit, not an optimizer or a performance benchmark.

Run in a fresh process: changes TILE_COST only in this process, restores it on
exit, never changes solvers, levels, production defaults or heuristic code.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
import json
from math import isclose, isfinite
from pathlib import Path
import subprocess

from gameModel.block import Block, Direction, Orientation
from gameModel.board import Board, Tile, TILE_COST
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import validate_solution
from search import astar, bfs, ucs
from search.contracts import SearchLimits
from search.heuristics import relaxed_distance

ROOT = Path(__file__).resolve().parents[1]
POLICIES = {
    'current': (4, .75, False),
    'upstream_weights_extended': (5, .5, False),
    'unit': (1, 1, True),
    'fragile_2': (2, .75, False),
    'fragile_8': (8, .75, False),
    'switch_0_5': (4, .5, False),
    'switch_1': (4, 1, False),
}


@contextmanager
def policy(name):
    old = dict(TILE_COST)
    fragile, switch, unit = POLICIES[name]
    try:
        TILE_COST.update({Tile.FRAGILE:fragile,Tile.SOFT_SWITCH:switch,
                          Tile.HEAVY_SWITCH:switch,Tile.SPLIT_SWITCH:switch})
        yield unit
    finally:
        TILE_COST.clear()
        TILE_COST.update(old)


def reference_cost(state, action, child, *, unit=False):
    """Independent expression of the stated landing-cell policy."""
    if unit or action == Direction.SWITCH:
        return 1.0
    block = child.block
    cells = block.occupied()
    if state.block.orientation == block.orientation == Orientation.SPLIT:
        cells = [block.cubes[block.active]]
    values = [child.board.getTile(*p) for p in cells]
    if Tile.VOID in values:
        return float('inf')
    return float(max(TILE_COST[t] for t in values))


def replay_metrics(problem, actions):
    state, cost = problem.initial.copy(), 0.0
    snapshot = problem.initial.copy()
    counts = Counter()
    for action in actions:
        child = problem.result(state,action)
        if child is None:
            raise AssertionError('Invalid replay edge')
        actual = problem.step_cost(state,action,child)
        expected = reference_cost(state,action,child,unit=problem.unit_cost)
        assert isfinite(actual) and actual > 0 and isclose(actual,expected)
        cost += actual
        if action == Direction.SWITCH:
            counts['control_switch'] += 1
        else:
            block = child.block
            cells = block.occupied()
            if state.block.orientation == block.orientation == Orientation.SPLIT:
                cells = [block.cubes[block.active]]
            tiles = [child.board.getTile(*p) for p in cells]
            counts['fragile_charged_steps'] += int(Tile.FRAGILE in tiles)
            counts['discounted_switch_steps'] += int(max(TILE_COST[t] for t in tiles)<1)
            counts['split_events'] += int(state.block.orientation != Orientation.SPLIT
                                         and block.orientation == Orientation.SPLIT)
        state = child
    assert problem.goal_test(state) and problem.initial == snapshot
    return {'steps':len(actions),'cost':cost,'exposure':dict(counts)}


def cases():
    for number in range(1,11):
        path = ROOT/f'levels/level{number}.json'
        board,block = loadLevelFromJson(path,False)
        yield f'campaign_{number:02d}',State(board,block).copy(),sha256(path.read_bytes()).hexdigest()
    # The same hand-made board across all policies, unlike changing a fixture
    # to preserve an expected "weighted route is longer" assertion.
    board = Board(3,7,[[Tile.NORMAL,Tile.FRAGILE,Tile.NORMAL,Tile.NORMAL,
                       Tile.FRAGILE,Tile.NORMAL,Tile.GOAL],
                      [Tile.NORMAL]*7,[Tile.NORMAL]*7])
    yield 'two_fragile_tradeoff',State(board,Block(0,0)),None
    board = Board(3,4,[[Tile.NORMAL,Tile.FRAGILE,Tile.NORMAL,Tile.GOAL],
                      [Tile.NORMAL]*4,[Tile.NORMAL]*4])
    yield 'one_fragile_tie',State(board,Block(0,0)),None


def run(timeout):
    revision = lambda ref: subprocess.check_output(['git','rev-parse',ref],cwd=ROOT,text=True).strip()
    report = {'baseline':revision('HEAD'),'upstream_original':revision('5571989'),
              'upstream_tip':revision('upstream/main'),
              'purpose':'Sensitivity and correctness, not preference optimality or runtime benchmark',
              'limits':{'timeout_seconds':timeout,'max_expanded_nodes':1000000},
              'policies':{name:{'fragile':f,'switch':s,'unit_cost':u}
                          for name,(f,s,u) in POLICIES.items()},'cases':[]}
    limits = SearchLimits(timeout_seconds=timeout)
    for name,initial,fingerprint in cases():
        case = {'case':name,'data_sha256':fingerprint,'results':{}}
        with policy('unit'):
            problem = Problem(initial.copy(),unit_cost=True)
            shortest = bfs.solve(problem,limits)
            assert shortest.status == 'solved', (name,shortest.status)
            validate_solution(problem,shortest)
        case['minimum_steps'] = len(shortest.actions)
        for model in POLICIES:
            with policy(model) as unit:
                problem = Problem(initial.copy(),unit_cost=unit)
                before = problem.initial.copy()
                results = {}
                for algorithm,solver,heuristic in [('ucs',ucs.solve,None),
                                                    ('astar_relaxed',astar.solve,relaxed_distance)]:
                    result = solver(problem,limits,heuristic)
                    row = {'status':result.status,'expanded':result.expanded_nodes,
                           'generated':result.generated_nodes,'cost':result.total_cost,
                           'actions':[a.name for a in result.actions]}
                    if result.status == 'solved':
                        validate_solution(problem,result)
                        row.update(replay_metrics(problem,result.actions))
                    results[algorithm] = row
                assert problem.initial == before
                if all(row['status']=='solved' for row in results.values()):
                    results['cost_agreement'] = isclose(results['ucs']['cost'],results['astar_relaxed']['cost'])
                    assert results['cost_agreement'], (name,model,results)
                    if unit:
                        assert results['ucs']['steps']==case['minimum_steps']
                results['shortest_path_scored_here'] = replay_metrics(problem,shortest.actions)
                case['results'][model] = results
        report['cases'].append(case)
        print(f'Checked {name}: {len(POLICIES)} policies',flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=30)
    args = parser.parse_args()
    report = run(args.timeout)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Evidence:',args.output)


if __name__ == '__main__':
    main()
