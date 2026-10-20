"""Person 1: implement BFS with discovery on enqueue. See docs/CONTRACT.md.

Count valid successors before duplicate filtering; check goal on dequeue before
limits; compute path cost with step_cost. Never mutate stored states.
The source search/bfs/bfsa.py is reference code only.
"""
from search.contracts import SearchResult


def solve(problem, limits, heuristic=None) -> SearchResult:
    """Ignore heuristic; enforce limits with perf_counter, including generation."""
    raise NotImplementedError("BFS chua trien khai (search/bfs.py)")
