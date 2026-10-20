"""Person 3: UCS using best_g and a monotonic heap tie counter.

Skip stale entries, then check goal, limits and expand. Count valid successors
before duplicate filtering. See docs/CONTRACT.md; never compare State in heaps.
"""
from search.contracts import SearchResult


def solve(problem, limits, heuristic=None) -> SearchResult:
    """Ignore heuristic; use the shared positive finite problem.step_cost()."""
    raise NotImplementedError("UCS chua trien khai (search/ucs.py)")
