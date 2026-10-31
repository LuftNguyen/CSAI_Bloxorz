"""Measure DFS on the current campaign; replay outside the measured solve().

Run from the repository root with python -m examples.benchmark_dfs.
Only --output writes a report. No GUI or third-party dependencies are needed.
"""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import platform
import subprocess

from gameModel.block import Direction
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search.contracts import SearchLimits


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repeats', type=int, default=3)
    parser.add_argument('--timeout', type=float, default=60.0)
    parser.add_argument('--max-expanded', type=int, default=1_000_000)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    if not isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be positive and finite')
    if args.max_expanded < 0:
        parser.error('--max-expanded must be nonnegative')

    limits = SearchLimits(args.timeout, args.max_expanded)
    sources = sorted(set(ROOT.glob('gameModel/*.py')) | {
        ROOT / name for name in (
            'search/dfs.py', 'search/contracts.py', 'search/registry.py',
            'runner.py', 'levels/levelLoader.py', 'examples/benchmark_dfs.py',
        )
    })
    level_paths = [ROOT / f'levels/level{number}.json' for number in range(1, 11)]
    report = {
        'format_version': 1,
        'algorithm': 'dfs',
        'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
        'base_revision': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True,
        ).strip(),
        'source_sha256': {
            path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in sources
        },
        'level_sha256': {
            path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in level_paths
        },
        'environment': {
            'python': platform.python_version(),
            'platform': platform.platform(),
            'processor': platform.processor(),
        },
        'measurement': 'runner.run_search; perf_counter; tracemalloc peak bytes',
        'validation': 'goal/cost replay and initial-state preservation outside timing',
        'limits': {'timeout_seconds': args.timeout, 'max_expanded_nodes': args.max_expanded},
        'repeats': args.repeats,
        'runs': [],
    }
    for mode in ('unit',):
        for number, path in enumerate(level_paths, 1):
            for repeat in range(1, args.repeats + 1):
                board, block = loadLevelFromJson(path, isDebug=False)
                problem = Problem(State(board, block).copy())
                snapshot = problem.initial.copy()
                initial_hash = hash(problem.initial)
                run = run_search(problem, 'dfs', limits)
                result = run.search
                validate_solution(problem, result)
                if (problem.initial != snapshot or hash(problem.initial) != initial_hash
                        or problem.initial.board.__dict__ != snapshot.board.__dict__):
                    raise ValueError('DFS or replay mutated the initial state')
                report['runs'].append({
                    'level': number, 'cost_mode': mode, 'repeat': repeat,
                    'status': result.status, 'steps': len(result.actions),
                    'rolls': sum(action != Direction.SWITCH for action in result.actions),
                    'total_cost': result.total_cost,
                    'expanded_nodes': result.expanded_nodes,
                    'generated_nodes': result.generated_nodes,
                    'search_time_seconds': run.search_time_seconds,
                    'peak_memory_bytes': run.peak_memory_bytes,
                    'solution_sha256': sha256(
                        ' '.join(action.name for action in result.actions).encode()
                    ).hexdigest(),
                    'replay_verified': result.status == 'solved',
                    'initial_state_preserved': True,
                })
                print(f'{mode} level={number} repeat={repeat} {result.status} '
                      f'steps={len(result.actions)} cost={result.total_cost} '
                      f'time={run.search_time_seconds:.6f}s peak={run.peak_memory_bytes}B',
                      flush=True)
    if args.output is not None:
        args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n',
                               encoding='utf-8')
        print(f'Report: {args.output}')


if __name__ == '__main__':
    main()
