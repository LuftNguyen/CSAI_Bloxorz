"""Uniform-cost graph search following the shared search contract."""
from heapq import heappop, heappush
from itertools import count
from math import isfinite
from time import perf_counter

from search.contracts import SearchLimits, SearchResult


def solve(problem, limits, heuristic=None) -> SearchResult:
    """Minimize shared step costs without mutating states or using heuristic."""
    # Validate here as well as in runner: solve() can be called directly.
    if not isinstance(limits, SearchLimits):
        raise TypeError("limits must be SearchLimits")
    if not isfinite(limits.timeout_seconds) or limits.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    if type(limits.max_expanded_nodes) is not int or limits.max_expanded_nodes < 0:
        raise ValueError("max_expanded_nodes must be a nonnegative integer")

    deadline = perf_counter() + limits.timeout_seconds
    initial = problem.initial
    expanded_nodes = 0
    generated_nodes = 0
    best_g = {initial: 0.0}
    parent = {}
    tie_counter = count()
    # A unique counter prevents heapq from comparing State objects on ties.
    frontier = [(0.0, next(tie_counter), initial)]

    def failure(status):
        return SearchResult(status, (), None, expanded_nodes, generated_nodes)

    while frontier:
        g, _, state = heappop(frontier)

        # A cheaper path leaves the old entry in the heap; it is not expanded.
        if g != best_g[state]:
            continue

        # Only a valid minimum-cost pop certifies an optimal goal. The contract
        # gives this goal precedence over timeout and expansion limits.
        if problem.goal_test(state):
            actions = []
            current = state
            while current != initial:
                previous, action = parent[current]
                actions.append(action)
                current = previous
            actions.reverse()
            return SearchResult(
                status="solved",
                actions=tuple(actions),
                total_cost=g,
                expanded_nodes=expanded_nodes,
                generated_nodes=generated_nodes,
            )

        if perf_counter() >= deadline:
            return failure("timeout")
        if expanded_nodes >= limits.max_expanded_nodes:
            return failure("node_limit")

        # Count the start of an expansion, even for a dead end or a later timeout.
        expanded_nodes += 1
        for action in problem.actions(state):
            if perf_counter() >= deadline:
                return failure("timeout")

            child = problem.result(state, action)
            if child is None:
                continue

            # Include valid duplicates; exclude invalid moves and the initial node.
            generated_nodes += 1
            step = float(problem.step_cost(state, action, child))
            if not isfinite(step) or step <= 0:
                raise ValueError("Step cost must be positive and finite")

            candidate_g = g + step
            if not isfinite(candidate_g):
                raise ValueError("Accumulated cost must be finite")

            if candidate_g < best_g.get(child, float("inf")):
                best_g[child] = candidate_g
                parent[child] = (state, action)
                heappush(frontier, (candidate_g, next(tie_counter), child))

    # The last transition can overrun the deadline without adding a heap entry.
    if perf_counter() >= deadline:
        return failure("timeout")
    return failure("unsolvable")
