"""Person 2: DFS with cycle prevention; reverse successors when pushing a stack.

See docs/CONTRACT.md for goal/limit order, counters and path cost. Agree on an
IDS depth-limit interface separately before adding IDS. No GUI or tracemalloc.
"""
from search.contracts import SearchResult


def solve(problem, limits, heuristic=None) -> SearchResult:
    """Ignore heuristic; use problem.actions(), preserve initial and stored states."""
    raise NotImplementedError("DFS chua trien khai (search/dfs.py)")
