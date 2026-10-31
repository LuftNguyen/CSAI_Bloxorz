import argparse
import csv
from pathlib import Path

from gameModel.problem import Problem
from gameModel.state import State
from levels.levelLoader import loadLevelFromJson
from runner import run_search
from search import heuristics
from search.contracts import SearchLimits

ROOT = Path(__file__).resolve().parents[1]
LAMBDAS = (0.0, 0.25, 0.5, 1.0, 3.0)  # đều biểu diễn chính xác trong nhị phân
FIELDS = ["level", "lambda", "status", "moves", "cost", "fragile_steps",
          "ucs_expanded", "ucs_time_s", "ucs_peak_kb",
          "astar_cost", "astar_expanded", "astar_time_s", "astar_matches_ucs"]


def fragile_steps(initial, actions):
    """Đếm số bước đáp lên fragile: replay với λ = 1 thì (cost - 1) chính là chỉ báo I."""
    probe = Problem(initial.copy(), fragile_penalty=1.0)
    state, count = probe.initial, 0
    for action in actions:
        child = probe.result(state, action)
        count += probe.step_cost(state, action, child) - 1.0
        state = child
    return int(round(count))


def load(level):
    board, block = loadLevelFromJson(ROOT / f"levels/level{level}.json", False)
    return State(board, block).copy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--levels", type=int, nargs="*", default=list(range(1, 11)))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    limits = SearchLimits(args.timeout)
    rows = []
    for level in args.levels:
        initial = load(level)
        for lam in LAMBDAS:
            ucs = run_search(Problem(initial.copy(), fragile_penalty=lam), "ucs", limits)
            s = ucs.search
            row = {"level": level, "lambda": lam, "status": s.status}
            if s.status == "solved":
                astar = run_search(Problem(initial.copy(), fragile_penalty=lam), "astar",
                                   limits, heuristics.relaxed_distance)
                a = astar.search
                row.update(
                    moves=len(s.actions), cost=s.total_cost,
                    fragile_steps=fragile_steps(initial, s.actions),
                    ucs_expanded=s.expanded_nodes, ucs_time_s=round(ucs.search_time_seconds, 4),
                    ucs_peak_kb=round(ucs.peak_memory_bytes / 1024, 1),
                    astar_cost=a.total_cost, astar_expanded=a.expanded_nodes,
                    astar_time_s=round(astar.search_time_seconds, 4),
                    astar_matches_ucs=(a.status == "solved"
                                       and abs(a.total_cost - s.total_cost) < 1e-9))
            rows.append(row)
            print(row, flush=True)
    if args.output:
        with args.output.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    main()