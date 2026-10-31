r"""Create 5 report-ready charts and a table from benchmark_all.py CSV output.

Usage (repo root):
    .\.venv\Scripts\python.exe -m pip install matplotlib
    .\.venv\Scripts\python.exe plot_benchmark.py benchmark_full
"""

from __future__ import annotations

import csv
from pathlib import Path
import sys

try:
    import matplotlib.pyplot as plt
except ImportError:
    raise SystemExit("Missing matplotlib: .\\.venv\\Scripts\\python.exe -m pip install matplotlib")

LABELS = {
    "bfs": "BFS", "dfs": "DFS", "ucs": "UCS",
    "astar_zero": "A* (h=0)", "astar_manhattan": "A* (Manhattan)",
    "astar_relaxed": "A* (Relaxed)",
}
METRICS = [
    ("median_time_s", "Search time (s)", "01_search_time.png", "Search time by level"),
    ("median_peak_memory_mb", "Peak Python memory (MB)", "02_peak_memory.png", "Peak traced memory by level"),
    ("median_expanded_nodes", "Expanded nodes", "03_expanded_nodes.png", "Expanded nodes by level"),
    ("median_solution_length", "Solution length (actions)", "04_solution_length.png", "Solution length by level"),
    ("median_total_cost", "Total path cost", "05_total_cost.png", "Solution cost by level"),
]


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def numeric(value):
    if value is None or value == "":
        return float("nan")
    return float(value)


def main():
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("benchmark_full")
    data = rows(directory / "level_summary.csv")
    if not data:
        raise SystemExit("level_summary.csv is empty; run benchmark_all.py first")
    figures = directory / "charts"
    figures.mkdir(exist_ok=True)
    configs = list(dict.fromkeys(r["config"] for r in data))
    level_nums = sorted({int(r["level"]) for r in data})
    lookup = {(int(r["level"]), r["config"]): r for r in data}
    for col, ylabel, filename, title in METRICS:
        fig, ax = plt.subplots(figsize=(10, 5.4))
        for cfg in configs:
            y = [numeric(lookup.get((lv, cfg), {}).get(col)) for lv in level_nums]
            ax.plot(level_nums, y, marker="o", markersize=3.5, linewidth=1.6,
                    label=LABELS.get(cfg, cfg))
        ax.set_title(title)
        ax.set_xlabel("Level")
        ax.set_ylabel(ylabel)
        ax.set_xticks(level_nums)
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, ncol=3, loc="best")
        fig.tight_layout()
        destination = figures / filename
        fig.savefig(destination, dpi=200)
        plt.close(fig)
        print("Wrote", destination)
    print("All charts are ready. Use each chart's caption to state the level set and aggregation rule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
