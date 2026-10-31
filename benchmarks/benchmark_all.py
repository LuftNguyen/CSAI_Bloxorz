r"""Reproducible, headless benchmark for LuftNguyen/CSAI_Bloxorz.

Place this file in the benchmarks/ folder of CSAI_Bloxorz and run from repository root:
    .\.venv\Scripts\python.exe benchmarks/benchmark_all.py --levels 1 5 8 --repeats 1 --output-dir benchmark_smoke
    .\.venv\Scripts\python.exe benchmarks/benchmark_all.py --repeats 5 --output-dir benchmark_full

Standard library only. Solver timing + tracemalloc profiling are delegated
exclusively to the repository's runner.run_search(). Replays are outside timing.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import traceback

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gameModel.block import Direction
from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search, validate_solution
from search.contracts import SearchLimits
from search.heuristics import HEURISTICS

ROOT = REPO_ROOT
CONFIGS = {
    "bfs": ("bfs", None),
    "dfs": ("dfs", None),
    "ucs": ("ucs", None),
    "astar_zero": ("astar", "zero"),
    "astar_manhattan": ("astar", "manhattan"),
    "astar_relaxed": ("astar", "relaxed"),
}
FIELDS = [
    "level", "group", "config", "algorithm", "heuristic", "trial", "cost_mode",
    "status", "search_time_s", "peak_memory_bytes", "peak_memory_mb",
    "expanded_nodes", "generated_nodes", "solution_length", "roll_count",
    "total_cost", "replay_verified", "initial_state_preserved", "error",
]
LEVEL_FIELDS = [
    "level", "name", "group", "rows", "cols", "fragile_tiles",
    "soft_switches", "heavy_switches", "split_switches", "bridge_groups",
    "bridges_initially_open", "bridges_initially_closed", "fatal_close_switches",
    "fatal_split_switches", "level_sha256",
]
LEVEL_SUMMARY_FIELDS = [
    "level", "group", "config", "algorithm", "heuristic", "trials", "solved_runs",
    "success_rate", "status_counts", "median_time_s", "median_peak_memory_mb",
    "median_expanded_nodes", "median_generated_nodes", "median_solution_length",
    "median_total_cost",
]
OVERALL_FIELDS = [
    "config", "algorithm", "heuristic", "levels_tested", "trials", "solved_runs",
    "success_rate", "status_counts", "median_time_s", "median_peak_memory_mb",
    "median_expanded_nodes", "median_generated_nodes", "median_solution_length",
    "median_total_cost", "note",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def git_revision():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL, timeout=5,
        ).strip()
    except (FileNotFoundError, subprocess.SubprocessError):
        return "unknown"


def git_dirty():
    try:
        return bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL, timeout=5,
        ).strip())
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def median_from(records, key):
    values = [float(row[key]) for row in records if row.get(key) not in (None, "")]
    return round(statistics.median(values), 8) if values else ""


def put_csv(path: Path, fields, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_level_info(level: int):
    path = ROOT / "levels" / f"level{level}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    groups = {1: "basic", 2: "basic", 3: "fragile", 4: "fragile",
              5: "bridge_switch", 6: "bridge_switch", 7: "bridge_switch",
              8: "split", 9: "split", 10: "split"}
    counts = Counter("".join(data["grid"]))
    bridges = data.get("bridges", [])
    return {
        "level": level, "name": data.get("name", f"Level {level}"),
        "group": groups[level], "rows": data["rows"], "cols": data["cols"],
        "fragile_tiles": counts["F"], "soft_switches": counts["w"],
        "heavy_switches": counts["W"], "split_switches": counts["T"],
        "bridge_groups": len(bridges),
        "bridges_initially_open": sum(b.get("initial_open", False) for b in bridges),
        "bridges_initially_closed": sum(not b.get("initial_open", False) for b in bridges),
        "fatal_close_switches": sum(bool(s.get("fatal_close")) for s in data.get("switches", [])),
        "fatal_split_switches": sum(bool(s.get("fatal_split")) for s in data.get("splits", [])),
        "level_sha256": sha256(path.read_bytes()).hexdigest(),
    }


def summarize(raw, level_info, configs):
    per_level = defaultdict(list)
    by_config = defaultdict(list)
    for row in raw:
        per_level[(row["level"], row["config"])].append(row)
        by_config[row["config"]].append(row)
    level_summaries = []
    for level in sorted(level_info):
        for config in configs:
            rows = per_level.get((level, config), [])
            if not rows:
                continue
            solved = [r for r in rows if r["status"] == "solved"]
            statuses = Counter(r["status"] for r in rows)
            algorithm, heuristic = CONFIGS[config]
            level_summaries.append({
                "level": level, "group": level_info[level]["group"],
                "config": config, "algorithm": algorithm, "heuristic": heuristic or "none",
                "trials": len(rows), "solved_runs": len(solved),
                "success_rate": round(len(solved) / len(rows), 5),
                "status_counts": json.dumps(statuses, sort_keys=True),
                "median_time_s": median_from(rows, "search_time_s"),
                "median_peak_memory_mb": median_from(rows, "peak_memory_mb"),
                "median_expanded_nodes": median_from(rows, "expanded_nodes"),
                "median_generated_nodes": median_from(rows, "generated_nodes"),
                "median_solution_length": median_from(solved, "solution_length"),
                "median_total_cost": median_from(solved, "total_cost"),
            })
    overall = []
    for config in configs:
        rows = by_config.get(config, [])
        if not rows:
            continue
        per = [r for r in level_summaries if r["config"] == config]
        solved = [r for r in rows if r["status"] == "solved"]
        statuses = Counter(r["status"] for r in rows)
        algorithm, heuristic = CONFIGS[config]
        overall.append({
            "config": config, "algorithm": algorithm, "heuristic": heuristic or "none",
            "levels_tested": len(per), "trials": len(rows), "solved_runs": len(solved),
            "success_rate": round(len(solved) / len(rows), 5),
            "status_counts": json.dumps(statuses, sort_keys=True),
            "median_time_s": median_from(per, "median_time_s"),
            "median_peak_memory_mb": median_from(per, "median_peak_memory_mb"),
            "median_expanded_nodes": median_from(per, "median_expanded_nodes"),
            "median_generated_nodes": median_from(per, "median_generated_nodes"),
            "median_solution_length": median_from(per, "median_solution_length"),
            "median_total_cost": median_from(per, "median_total_cost"),
            "note": "median of per-level medians; solution metrics exclude unsolved runs",
        })
    return level_summaries, overall


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max-expanded", type=int, default=1_000_000)
    parser.add_argument("--cost-mode", choices=("tile", "unit"), default="tile")
    parser.add_argument("--levels", type=int, nargs="+", default=list(range(1, 11)))
    parser.add_argument("--configs", nargs="+", choices=tuple(CONFIGS),
                        default=list(CONFIGS))
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results"))
    parser.add_argument("--seed", type=int, default=20261030)
    args = parser.parse_args()
    if args.repeats < 1 or args.max_expanded < 0 or not isfinite(args.timeout) or args.timeout <= 0:
        parser.error("repeats >= 1, max-expanded >= 0, timeout > 0 and finite are required")
    if any(level < 1 or level > 10 for level in args.levels):
        parser.error("--levels must be between 1 and 10")
    levels = sorted(set(args.levels))
    configs = list(dict.fromkeys(args.configs))
    worktree_dirty_before_run = git_dirty()
    outdir = args.output_dir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    limits = SearchLimits(timeout_seconds=args.timeout, max_expanded_nodes=args.max_expanded)
    level_info = {level: make_level_info(level) for level in levels}
    put_csv(outdir / "levels.csv", LEVEL_FIELDS, level_info.values())

    files = [ROOT / "runner.py", ROOT / "gameModel" / "problem.py",
             ROOT / "search" / "registry.py", ROOT / "search" / "contracts.py",
             ROOT / "search" / "heuristics.py", ROOT / "levels" / "levelLoader.py",
             ROOT / "benchmarks" / "benchmark_all.py"]
    files += list((ROOT / "gameModel").glob("*.py"))
    files += list((ROOT / "search").glob("*.py"))
    files = sorted(set(p for p in files if p.is_file()))
    metadata = {
        "date_utc": utc_now(), "repository": "LuftNguyen/CSAI_Bloxorz",
        "git_revision": git_revision(), "git_worktree_dirty": worktree_dirty_before_run,
        "python": platform.python_version(), "platform": platform.platform(),
        "processor": platform.processor(), "logical_cpus": __import__("os").cpu_count(),
        "levels": levels, "configs": configs, "repeats": args.repeats,
        "cost_mode": args.cost_mode, "seed": args.seed,
        "limits": {"timeout_seconds": args.timeout,
                   "max_expanded_nodes": args.max_expanded},
        "time_method": "perf_counter around solve() via runner.run_search",
        "memory_method": "tracemalloc Python peak, bytes / 1_000_000 = MB (not process RSS)",
        "validation": "runner.validate_solution replay after measurement",
        "aggregation": "median within each level/config; then median across levels (equal level weights)",
        "source_sha256": {p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
                          for p in files},
        "level_sha256": {f"level{lv}.json": level_info[lv]["level_sha256"] for lv in levels},
    }
    (outdir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    jobs = [(lv, cfg, repeat) for lv in levels for cfg in configs for repeat in range(1, args.repeats + 1)]
    random.Random(args.seed).shuffle(jobs)
    raw = []
    errors_path = outdir / "errors.txt"
    errors_path.write_text("", encoding="utf-8")
    print(f"Benchmark: {len(jobs)} sequential runs; results in {outdir}", flush=True)
    with (outdir / "runs.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index, (level, config, trial) in enumerate(jobs, 1):
            algorithm, heuristic_name = CONFIGS[config]
            row = {
                "level": level, "group": level_info[level]["group"],
                "config": config, "algorithm": algorithm,
                "heuristic": heuristic_name or "none", "trial": trial,
                "cost_mode": args.cost_mode, "status": "error",
                "search_time_s": "", "peak_memory_bytes": "", "peak_memory_mb": "",
                "expanded_nodes": "", "generated_nodes": "",
                "solution_length": "", "roll_count": "", "total_cost": "",
                "replay_verified": "", "initial_state_preserved": "", "error": "",
            }
            try:
                board, block = loadLevelFromJson(
                    ROOT / "levels" / f"level{level}.json", isDebug=False)
                problem = Problem(State(board, block).copy(), unit_cost=(args.cost_mode == "unit"))
                snapshot = problem.initial.copy()
                original_hash = hash(problem.initial)
                heuristic = HEURISTICS[heuristic_name] if heuristic_name else None
                measured = run_search(problem, algorithm, limits, heuristic=heuristic)
                result = measured.search
                validated = False
                if result.status == "solved":
                    validate_solution(problem, result)
                    validated = True
                state_preserved = problem.initial == snapshot and hash(problem.initial) == original_hash
                if not state_preserved:
                    raise ValueError("Initial state was changed by solver or validation")
                row.update({
                    "status": result.status, "search_time_s": round(measured.search_time_seconds, 9),
                    "peak_memory_bytes": measured.peak_memory_bytes,
                    "peak_memory_mb": round(measured.peak_memory_bytes / 1_000_000, 9),
                    "expanded_nodes": result.expanded_nodes,
                    "generated_nodes": result.generated_nodes,
                    "solution_length": len(result.actions) if validated else "",
                    "roll_count": (sum(action != Direction.SWITCH for action in result.actions)
                                   if validated else ""),
                    "total_cost": result.total_cost if validated else "",
                    "replay_verified": validated if validated else "",
                    "initial_state_preserved": True,
                })
            except Exception as exc:
                row["status"] = "error"
                row["error"] = f"{type(exc).__name__}: {exc}"
                with errors_path.open("a", encoding="utf-8") as error_file:
                    error_file.write(f"\nlevel={level} config={config} trial={trial}\n")
                    traceback.print_exc(file=error_file)
            writer.writerow(row)
            handle.flush()   # partial results survive an interrupted benchmark
            raw.append(row)
            print(f"[{index:3d}/{len(jobs)}] level={level:2d} {config:17} "
                  f"trial={trial} {row['status']:11} "
                  f"time={row['search_time_s']} steps={row['solution_length']} "
                  f"cost={row['total_cost']}", flush=True)

    levels_summary, overall_summary = summarize(raw, level_info, configs)
    put_csv(outdir / "level_summary.csv", LEVEL_SUMMARY_FIELDS, levels_summary)
    put_csv(outdir / "overall_summary.csv", OVERALL_FIELDS, overall_summary)
    print("\nDone. Files: runs.csv, levels.csv, level_summary.csv, overall_summary.csv, metadata.json, errors.txt")
    if any(r["status"] == "error" for r in raw):
        print("WARNING: one or more runs raised exceptions; inspect errors.txt", file=sys.stderr)
        return 2
    if any(r["status"] != "solved" for r in raw):
        print("NOTE: some runs were not solved; compare success rates and status before other metrics")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
