"""Person 4: A* using best_g, stale-entry filtering and reopening cheaper states.

Use a monotonic heap tie counter. Check goal before limits after stale filtering.
See docs/CONTRACT.md for counters, limits and result semantics.
"""
from search.contracts import SearchResult


def solve(problem, limits, heuristic=None) -> SearchResult:
    """Use heuristic(problem, state), or zero if None. No GUI or tracemalloc."""
    raise NotImplementedError("A* chua trien khai (search/astar.py)")
