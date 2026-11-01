"""New Windows cohort, separate from upstream macOS; append-only raw JSONL.

140 survey solves are needed because historical CSVs lack actions and measured F.
Survey: one repetition, descriptive timing only. Selected cases: three repetitions.
Default-cost historical verification: missing unique configurations only, untimed.
Resume skips completed keys, refuses changed production source or environment.
"""
from common import BASE, ROOT, digest, read_csv, write_csv, write_json, provenance
from collections import defaultdict
import argparse
import gc
import json
import math
import random
import statistics
import time
import traceback
import tracemalloc

from gameModel.block import Direction
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search.contracts import SearchLimits
from search.registry import get_solver
from search import heuristics as H

LAMBDAS = (0., .25, .5, 1., 1.5, 2., 3.)
SEED = 20261030
LIMITS = SearchLimits(timeout_seconds=60., max_expanded_nodes=1_000_000)
PRE = {'astar_relaxed':H.precompute, 'astar_relaxed_split':H.precompute_split}
RAW = BASE/'cost_sensitivity/raw'


def new_problem(level, lam, unit=False):
    board, block = loadLevelFromJson(ROOT/'levels'/f'level{level}.json', isDebug=False)
    return Problem(State(board, block).copy(), unit_cost=unit, fragile_penalty=lam)


def replay(problem, result):
    """Count F by invoking real step_cost with lambda=1, also when lambda=0.

    No hand-written approximation of split/teleport/merge footprint is used.
    The actual-mode cost is summed independently and checked by validate_solution.
    """
    validate_solution(problem, result)
    if result.status != 'solved':
        return {'replay_verified': False, 'actions': [], 'step_trace': [],
                'fragile_penalty_count': None, 'solution_length': None, 'roll_count': None}
    state = problem.initial.copy()
    probe = Problem(state.copy(), unit_cost=False, fragile_penalty=1.)
    f, total, trace = 0, 0., []
    for index, action in enumerate(result.actions, 1):
        child = problem.result(state, action)
        if child is None:
            raise ValueError('Invalid replay transition')
        indicator = probe.step_cost(state, action, child)-1.
        if indicator not in (0., 1.):
            raise ValueError('Cost no longer has binary fragile indicator')
        step = problem.step_cost(state, action, child)
        expected = 1. if problem.unit_cost else 1.+problem.fragile_penalty*indicator
        if step != expected or (action == Direction.SWITCH and step != 1.):
            raise ValueError('Cost model mismatch')
        f += int(indicator)
        total += step
        trace.append({'index':index,'action':action.name,'cost':step,'penalty_indicator':int(indicator),
                      'before_orientation':state.block.orientation.name,'after_orientation':child.block.orientation.name,
                      'occupied_after':child.block.occupied(),'active_after':child.block.active})
        state = child
    if not math.isclose(total, result.total_cost, abs_tol=1e-9):
        raise ValueError('Accumulated replay cost mismatch')
    if not problem.unit_cost and total != len(result.actions)+problem.fragile_penalty*f:
        raise ValueError('C != N + lambda F')
    return {'replay_verified': True, 'actions':[a.name for a in result.actions], 'step_trace':trace,
            'action_sha256':digest(json.dumps([a.name for a in result.actions]).encode()),
            'fragile_penalty_count':f, 'solution_length':len(result.actions),
            'roll_count':sum(a != Direction.SWITCH for a in result.actions), 'replayed_total_cost':total}


def solve_one(level, lam, config, trial, phase, measured=True):
    gc.collect()
    p = new_problem(level, lam)
    snap, h0 = p.initial.copy(), hash(p.initial)
    algo = 'astar' if config.startswith('astar_') else config
    heuristic = H.HEURISTICS[config.removeprefix('astar_')] if algo == 'astar' else None
    row = {'phase':phase,'level':level,'lambda':lam,'config':config,'trial':trial,
           'cost_mode':'tile','cohort':'windows_supplement','metadata':'metadata/supplement_environment.json',
           'status':'error','error':'','search_time_s':None,'precompute_time_s':None,'total_time_s':None,
           'peak_memory_bytes':None,'peak_memory_mb':None,'precompute_peak_memory_mb':None,
           'expanded_nodes':None,'generated_nodes':None,'total_cost':None}
    try:
        if p in H._TABLES or p in H._SPLIT_TABLES:
            raise ValueError('Unexpected reused problem cache')
        if measured:
            pre_t, pre_peak = 0., 0
            if config in PRE:
                tracemalloc.start()
                try:
                    start = time.perf_counter()
                    PRE[config](p)
                    pre_t = time.perf_counter()-start
                    _, pre_peak = tracemalloc.get_traced_memory()
                finally:
                    tracemalloc.stop()
            run = run_search(p, algo, LIMITS, heuristic)
            result = run.search
            row.update(search_time_s=run.search_time_seconds, precompute_time_s=pre_t,
                       total_time_s=pre_t+run.search_time_seconds, peak_memory_bytes=run.peak_memory_bytes,
                       peak_memory_mb=run.peak_memory_bytes/1e6, precompute_peak_memory_mb=pre_peak/1e6)
        else:
            result = get_solver(algo)(p, LIMITS, heuristic)
        row.update(status=result.status, total_cost=result.total_cost,
                   expanded_nodes=result.expanded_nodes, generated_nodes=result.generated_nodes)
        row.update(replay(p, result))
        row['initial_state_preserved'] = p.initial == snap and hash(p.initial) == h0
        if not row['initial_state_preserved']:
            raise ValueError('Initial state mutated')
    except Exception:
        row.update(status='error', error=traceback.format_exc(), replay_verified=False)
    return row


def load_jsonl(path):
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def key(r):
    return r['level'], r['lambda'], r['config'], r['trial']


def run_jobs(jobs, path, existing):
    done = {key(r) for r in existing}
    todo = [j for j in jobs if j[:4] not in done]
    random.Random(SEED).shuffle(todo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        for i, (lv, lam, cfg, trial, phase, measured) in enumerate(todo, 1):
            row = solve_one(lv, lam, cfg, trial, phase, measured)
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')
            f.flush()
            existing.append(row)
            print(f'{phase} {i}/{len(todo)} L{lv} lambda={lam} {cfg} trial={trial}: {row["status"]} N={row.get("solution_length")} F={row.get("fragile_penalty_count")} C={row.get("total_cost")}', flush=True)
            if row['status'] != 'solved':
                raise RuntimeError('Supplement stopped; inspect raw error/status before continuing')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=['survey','cases','verify','all'], default='all')
    args = parser.parse_args()
    meta_path = BASE/'metadata/supplement_environment.json'
    meta = provenance()
    meta.update(lambdas=LAMBDAS, seed=SEED, limits={'timeout_seconds':60.,'max_expanded_nodes':1_000_000},
                survey_repetitions=1, case_repetitions=3, cost_mode='tile',
                time_method='Fresh Problem each solve. Explicit precompute traced separately, then runner.run_search; replay excluded.',
                memory_method='Separate phase Python tracemalloc peaks, MB=1e6 bytes. No combined/process peak claimed.',
                cache_policy='No reuse between runs; each new Problem builds its own weak-key heuristic cache.',
                survey_timing='Single observations, descriptive only. Cases have 3 repetitions. No pooling with macOS.',
                reuse_reason='Old CSV has no actions/step traces/F at lambda zero: fresh survey provides required direct evidence.')
    if meta_path.exists():
        old = json.loads(meta_path.read_text(encoding='utf-8'))
        prod = lambda d:{k:v for k,v in d['source_sha256_lf'].items() if not k.startswith('benchmarks/report_analysis/')}
        if prod(old) != prod(meta) or old['environment']['platform'] != meta['environment']['platform'] or old['environment']['python'] != meta['environment']['python']:
            raise ValueError('Resume source/environment mismatch')
    else:
        write_json(meta_path, meta)
    survey_path = RAW/'survey.jsonl'
    survey = load_jsonl(survey_path)
    if args.stage in ('survey','all'):
        run_jobs([(lv,lam,cfg,1,'survey',True) for lv in range(1,11) for lam in LAMBDAS for cfg in ('bfs','ucs')], survey_path, survey)
    if len(survey) != 140:
        raise ValueError('Need complete 140-row survey before selecting case studies')
    changed = []
    for lv in range(1,11):
        u = [r for r in survey if r['level']==lv and r['config']=='ucs']
        if len({(r['solution_length'],r['fragile_penalty_count']) for r in u}) > 1:
            changed.append(lv)
    selected = sorted(set([2,4]+changed))
    cases = load_jsonl(RAW/'cases_additional.jsonl')
    pairs = [(lv,lam) for lv in selected for lam in ((.25,1.,1.5,2.,3.) if lv==4 else (.25,3.))]
    write_json(BASE/'cost_sensitivity/case_studies/selection.json', {'selected_levels':selected,'N_or_F_changes':changed,'pairs':pairs,
                'selection_rule':'Mandatory L2,L4 plus every level with a UCS (N,F) change across surveyed lambdas. L4 bracket includes 1,1.5,2,3.',
                'threshold_policy':'Discrete grid observations are brackets, never an exact global optimum threshold.'})
    if args.stage in ('cases','all'):
        jobs = [(lv,lam,cfg,t,'case_study',True) for lv,lam in pairs for cfg in ('bfs','ucs','astar_relaxed','astar_relaxed_split') for t in range(1,4)
                if not (cfg in ('bfs','ucs') and t==1)]
        run_jobs(jobs, RAW/'cases_additional.jsonl', cases)
    verification = load_jsonl(BASE/'main_comparison/raw/direct_verification.jsonl')
    if args.stage in ('verify','all'):
        # Reuse same-source direct survey/case solutions for correctness, not timings.
        found = {(r['level'],r['config']):r for r in survey+cases if r['lambda']==.25}
        missing = [(lv,.25,cfg,1,'historical_correctness_verification',False) for lv in range(1,11)
                   for cfg in ('bfs','dfs','ucs','astar_zero','astar_manhattan','astar_relaxed','astar_relaxed_split') if (lv,cfg) not in found]
        run_jobs(missing, BASE/'main_comparison/raw/direct_verification.jsonl', verification)
        found.update({(r['level'],r['config']):r for r in verification})
        old = read_csv(BASE/'main_comparison/raw/upstream_weighted/runs.csv')
        checks=[]
        for r in old:
            x=found[(int(r['level']),r['config'])]
            fields=['solution_length','total_cost','expanded_nodes','generated_nodes','roll_count']
            ok=all(float(r[f])==float(x[f]) for f in fields) and x['replay_verified']
            checks.append({'level':r['level'],'config':r['config'],'trial':r['trial'],'historical_metrics_match_direct_solution':ok,
                           'direct_action_sha256':x['action_sha256'],'note':'Reconstructed deterministic solution; original CSV did not store actions. Historical timing is untouched.'})
        if not all(x['historical_metrics_match_direct_solution'] for x in checks):
            raise ValueError('Historical structural results do not reproduce')
        write_csv(BASE/'main_comparison/summary/direct_verification.csv',checks)
    print('Complete stage:',args.stage,flush=True)


if __name__ == '__main__':
    main()
