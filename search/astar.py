"""A* with best_g, stale-entry filtering and state reopening."""

from heapq import heappop, heappush
from itertools import count
from math import isfinite
from time import perf_counter

from search.contracts import SearchResult


def _evaluate_heuristic(problem, state, heuristic):
    if heuristic is None:
        return 0.0

    value = float(heuristic(problem, state))

    if not isfinite(value) or value < 0:
        raise ValueError(
            "Heuristic must return a finite, nonnegative number"
        )

    return value


def solve(problem, limits, heuristic=None) -> SearchResult:
    """Use heuristic(problem, state), or zero if None."""
    start_time = perf_counter()
    initial = problem.initial

    expanded_nodes = 0
    generated_nodes = 0

    if problem.goal_test(initial):
        return SearchResult(
            status="solved",
            actions=(),
            total_cost=0.0,
            expanded_nodes=0,
            generated_nodes=0,
        )

    best_g = {initial: 0.0}
    parent = {}

    tie_counter = count()
    frontier = []

    initial_h = _evaluate_heuristic(problem, initial, heuristic)
    heappush(
        frontier,
        (initial_h, next(tie_counter), 0.0, initial),
    )

    while frontier:
        _, _, g, state = heappop(frontier)

        # Bỏ mục heap cũ khi đã có đường rẻ hơn.
        if g != best_g[state]:
            continue

        # Kiểm tra đích và truy vết trước khi xét giới hạn.
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

        if perf_counter() - start_time >= limits.timeout_seconds:
            return SearchResult(
                status="timeout",
                actions=(),
                total_cost=None,
                expanded_nodes=expanded_nodes,
                generated_nodes=generated_nodes,
            )

        if expanded_nodes >= limits.max_expanded_nodes:
            return SearchResult(
                status="node_limit",
                actions=(),
                total_cost=None,
                expanded_nodes=expanded_nodes,
                generated_nodes=generated_nodes,
            )

        # Bắt đầu mở rộng node.
        expanded_nodes += 1

        for action in problem.actions(state):
            if perf_counter() - start_time >= limits.timeout_seconds:
                return SearchResult(
                    status="timeout",
                    actions=(),
                    total_cost=None,
                    expanded_nodes=expanded_nodes,
                    generated_nodes=generated_nodes,
                )

            child = problem.result(state, action)

            if perf_counter() - start_time >= limits.timeout_seconds:
                return SearchResult(
                    status="timeout",
                    actions=(),
                    total_cost=None,
                    expanded_nodes=expanded_nodes,
                    generated_nodes=generated_nodes,
                )
            
            if child is None:
                continue

            generated_nodes += 1

            step = float(problem.step_cost(state, action, child))

            if not isfinite(step) or step <= 0:
                raise ValueError(
                    "Step cost must be positive and finite"
                )

            new_g = g + step

            if not isfinite(new_g):
                raise ValueError(
                    "Accumulated cost must be finite"
                )
            
            if new_g >= best_g.get(child, float("inf")):
                continue

            child_h = _evaluate_heuristic(
                problem, child, heuristic
            )

            best_g[child] = new_g
            parent[child] = (state, action)

            heappush(
                frontier,
                (
                    new_g + child_h,
                    next(tie_counter),
                    new_g,
                    child,
                ),
            )

    return SearchResult(
        status="unsolvable",
        actions=(),
        total_cost=None,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
    )