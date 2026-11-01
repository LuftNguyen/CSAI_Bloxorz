"""Validate and snapshot upstream CSVs; no solver calls. Run from repo root."""
from common import BASE, ROOT, digest, read_csv, write_csv, write_json, provenance
from collections import Counter
from itertools import product
import importlib.util
import json
import math
import subprocess


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    spec = importlib.util.spec_from_file_location('official_benchmark', ROOT/'benchmarks/benchmark_all.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    reports = []
    for name in ['results', 'results_unit', 'results_lambda_0', 'results_lambda_0.25', 'results_lambda_0.5', 'results_lambda_1']:
        src = ROOT/'benchmarks'/name
        meta = json.loads((src/'metadata.json').read_text(encoding='utf-8'))
        raw = read_csv(src/'runs.csv')
        keys = Counter((int(r['level']), r['config'], int(r['trial'])) for r in raw)
        expected = set(product(meta['levels'], meta['configs'], range(1, meta['repeats']+1)))
        check(set(keys) == expected and all(n == 1 for n in keys.values()), f'{name}: missing/duplicate trials')
        check(meta['cost_mode'] == ('unit' if name == 'results_unit' else 'tile'), f'{name}: cost mode')
        check(meta['fragile_penalty'] == (None if name == 'results_unit' else 0.25 if name == 'results' else float(name.removeprefix('results_lambda_'))), f'{name}: lambda')
        for p, h in meta['source_sha256'].items():
            blob = subprocess.check_output(['git', 'show', meta.get('repository_snapshot', 'c4cc318')+':'+p], cwd=ROOT)
            check(digest(blob) == h, f'{name}: recorded source hash {p}')
            check(digest((ROOT/p).read_bytes().replace(b'\r\n', b'\n')) == h, f'{name}: current source LF differs {p}')
        for p, h in meta['level_sha256'].items():
            check(digest((ROOT/'levels'/p).read_bytes().replace(b'\r\n', b'\n')) == h, f'{name}: level {p}')
        for r in raw:
            check(r['status'] == 'solved' and r['replay_verified'] == 'True' and r['initial_state_preserved'] == 'True' and not r['error'], f'{name}: failed/unverified historical row')
            check(r['cost_mode'] == meta['cost_mode'], f'{name}: mixed cost mode')
            for k in ['search_time_s', 'precompute_time_s', 'total_time_s', 'peak_memory_mb', 'precompute_peak_memory_mb', 'expanded_nodes', 'generated_nodes', 'solution_length', 'total_cost']:
                check(math.isfinite(float(r[k])) and float(r[k]) >= 0, f'{name}: invalid {k}')
            check(abs(float(r['total_time_s'])-float(r['search_time_s'])-float(r['precompute_time_s'])) < 3e-9, f'{name}: time sum')
            check(abs(float(r['peak_memory_bytes'])/1e6-float(r['peak_memory_mb'])) < 2e-9, f'{name}: memory units')
            n, c = float(r['solution_length']), float(r['total_cost'])
            lam = meta['fragile_penalty']
            check(c >= n and int(r['roll_count']) <= n, f'{name}: cost/actions')
            if not lam:
                check(c == n, f'{name}: unit/zero lambda cost')
            else:
                f = (c-n)/lam
                check(abs(f-round(f)) < 1e-9 and 0 <= f <= n, f'{name}: cost formula invariant (not measured F)')
        typed = [dict(r, level=int(r['level'])) for r in raw]
        levels = {lv:mod.make_level_info(lv) for lv in meta['levels']}
        per, overall = mod.summarize(typed, levels, meta['configs'])
        for filename, calculated in [('level_summary.csv', per), ('overall_summary.csv', overall)]:
            old = read_csv(src/filename)
            check(len(old) == len(calculated), f'{name}/{filename}: row count')
            for a, b in zip(old, calculated):
                for k, v in b.items():
                    try:
                        equal = math.isclose(float(a[k]), float(v), rel_tol=1e-8, abs_tol=1e-8)
                    except (ValueError, TypeError):
                        equal = a[k] == str(v)
                    check(equal, f'{name}/{filename}: summary differs {k}: {a[k]} vs {v}')
        # Preserve exact bytes. Existing snapshots must match, never replace them.
        dst = BASE/('main_comparison/raw/upstream_weighted' if name == 'results' else 'metadata/historical_datasets/'+name)
        dst.mkdir(parents=True, exist_ok=True)
        for p in src.iterdir():
            if p.is_file():
                q = dst/p.name
                if q.exists():
                    check(q.read_bytes() == p.read_bytes(), f'Existing snapshot changed: {q}')
                else:
                    q.write_bytes(p.read_bytes())
        reports.append({'dataset': name, 'rows': len(raw), 'validation': 'PASS',
                        'original_replay_claim': True, 'actions_absent_in_original': True,
                        'source_matches_upstream_blob': True, 'current_source_matches_after_CRLF_to_LF': True,
                        'metadata': meta, 'files_sha256': {p.name:digest(p.read_bytes()) for p in src.iterdir() if p.is_file()}})
        if name == 'results':
            ucs = {r['level']:float(r['median_total_cost']) for r in per if r['config']=='ucs'}
            enriched = [dict(r, optimal_cost_baseline=ucs[r['level']], cost_gap_to_ucs=float(r['median_total_cost'])-ucs[r['level']], relative_cost_gap=(float(r['median_total_cost'])/ucs[r['level']]-1)) for r in per]
            write_csv(BASE/'main_comparison/summary/per_level.csv', enriched)
            write_csv(BASE/'main_comparison/summary/overall.csv', overall)
            write_csv(BASE/'main_comparison/summary/levels.csv', list(levels.values()))
            write_csv(BASE/'heuristic_comparison/summary/per_level.csv', [r for r in enriched if r['config'] not in ('bfs','dfs')])
            write_csv(BASE/'heuristic_comparison/summary/overall.csv', [r for r in overall if r['config'] not in ('bfs','dfs')])
    write_json(BASE/'metadata/historical_validation.json', {'datasets':reports,'total_rows':sum(x['rows'] for x in reports),'validator':provenance(),
        'timing_policy':'Historical macOS timings remain separate from new Windows measurements.',
        'plots_policy':'Original PNGs are not reused; derived figures will be regenerated from audited CSV.'})
    print('PASS: audited and preserved', sum(x['rows'] for x in reports), 'historical rows; no solver executed.')


if __name__ == '__main__':
    main()
