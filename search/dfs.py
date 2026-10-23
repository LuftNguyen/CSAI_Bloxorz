"""Person 2: DFS with cycle prevention; reverse successors when pushing a stack.

See docs/CONTRACT.md for goal/limit order, counters and path cost. Ordinary DFS
with repeated-state handling needs no depth limit on a finite state space.
Only depth-limited DFS or IDS would need further policy. Keep the shared solve
interface unchanged. No GUI or tracemalloc.
"""
from dataclasses import dataclass
from time import perf_counter

from gameModel.block import Direction
from search.contracts import SearchResult


@dataclass
class _Node:
    state: object
    parent: "_Node | None"
    action: Direction | None
    cost: float


def solve(problem, limits, heuristic=None) -> SearchResult:
    start = perf_counter()

    stack = [_Node(problem.initial, None, None, 0.0)]
    visited = set()

    expanded_nodes = 0
    generated_nodes = 0

    def timed_out():
        return perf_counter() - start >= limits.timeout_seconds

    def finish(status, actions=(), cost=None):
        return SearchResult(
            status=status,
            actions=actions,
            total_cost=cost,
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
        )

    while stack:
        node = stack.pop()

        # Một trạng thái có thể được đưa vào stack từ nhiều nhánh.
        # Chỉ mở rộng nó một lần.
        if node.state in visited:
            continue

        # Kiểm tra đích trước giới hạn theo contract.
        if problem.goal_test(node.state):
            actions = []
            current = node

            while current.parent is not None:
                actions.append(current.action)
                current = current.parent

            actions.reverse()
            return finish("solved", tuple(actions), node.cost)

        if timed_out():
            return finish("timeout")

        if expanded_nodes >= limits.max_expanded_nodes:
            return finish("node_limit")

        visited.add(node.state)
        expanded_nodes += 1

        successors = []

        for action in problem.actions(node.state):
            if timed_out():
                return finish("timeout")

            child = problem.result(node.state, action)

            # Đếm successor hợp lệ trước khi lọc trạng thái trùng.
            if child is not None:
                generated_nodes += 1

            if timed_out():
                return finish("timeout")

            if child is None or child in visited:
                continue

            cost = node.cost + problem.step_cost(
                node.state, action, child
            )

            successors.append(
                _Node(child, node, action, cost)
            )

        if timed_out():
            return finish("timeout")

        # Stack là LIFO: đẩy ngược để lấy ra đúng thứ tự actions().
        stack.extend(reversed(successors))

    return finish("unsolvable")