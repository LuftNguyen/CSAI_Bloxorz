"""Person 1: implement BFS with discovery on enqueue. See docs/CONTRACT.md.

Count valid successors before duplicate filtering; check goal on dequeue before
limits; compute path cost with step_cost. Never mutate stored states.
The source search/bfs/bfsa.py is reference code only.
"""
from search.contracts import SearchResult
from search.node import Node
from time import perf_counter
from collections import deque

def solve(problem, limits, heuristic=None) -> SearchResult:
    """Ignore heuristic; enforce limits with perf_counter, including generation."""
    # Use a monotonic clock to enforce the time budget throughout the search.
    deadline = perf_counter() + limits.timeout_seconds
    expanded_nodes = generated_nodes = 0
    root = Node(
        state=problem.initial,
        parent=None,
        action=None,
        path_cost=0.0
    )
    # A FIFO queue explores states in order of increasing move count.
    queue = deque([root])
    # Mark states as discovered when enqueued to prevent duplicate queue entries.
    visited = {root.state}
    while queue:
        node = queue.popleft()
        

        # Check the goal before limits so a dequeued solution takes precedence.
        if problem.goal_test(node.state):
            return SearchResult(status="solved",
                                actions=tuple(node.solution()),
                                total_cost=node.path_cost,
                                generated_nodes=generated_nodes,
                                expanded_nodes=expanded_nodes
                                )

        # Stop before expanding another state if either search limit is reached.
        if perf_counter() >= deadline:
                    return SearchResult(status="timeout",
                                        actions=(),
                                        total_cost=None,
                                        generated_nodes=generated_nodes,
                                        expanded_nodes=expanded_nodes)
        
        if expanded_nodes >= limits.max_expanded_nodes:
                return SearchResult(status="node_limit",
                                    actions=(),
                                    total_cost=None,
                                    expanded_nodes=expanded_nodes,
                                    generated_nodes=generated_nodes)

        # Count an expansion when we begin examining a state's possible moves.
        expanded_nodes += 1

        for action in problem.actions(node.state):
            # Successor generation must also respect the time budget.
            if perf_counter() >= deadline:
                 return SearchResult(status="timeout",
                                     actions=(),
                                     total_cost=None,
                                     generated_nodes=generated_nodes,
                                     expanded_nodes=expanded_nodes)


            next_state = problem.result(node.state, action)

            # Invalid moves produce no successor and do not count as generated.
            if next_state is None:
                continue
            # Count every valid successor, including previously discovered states.
            generated_nodes += 1


            if next_state not in visited:
                visited.add(next_state)
                # Accumulate actual move costs; BFS still orders by move count.
                path_cost=node.path_cost + problem.step_cost(node.state, action, next_state)
                # Keep the parent and action so the solution can be reconstructed.
                next_node = Node(state=next_state,
                                 parent=node,
                                 action=action,
                                 path_cost=path_cost)
                queue.append(next_node)

        
    # Exhausting the queue means no reachable state satisfies the goal.
    return SearchResult(status="unsolvable",
                        actions=(),
                        total_cost=None,
                        expanded_nodes=expanded_nodes,
                        generated_nodes=generated_nodes)
