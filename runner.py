"""Measure only solve(), including path reconstruction, without GUI imports.

Exceptions propagate as programming/data errors, never as unsolvable results.
One measurement per process; an existing external trace is left untouched.
"""
from dataclasses import dataclass
from math import isfinite
from threading import Lock
from time import perf_counter
import tracemalloc

from search.contracts import SearchLimits, SearchResult
from search.registry import get_solver


@dataclass(frozen=True)
class RunResult:
    search: SearchResult
    search_time_seconds: float
    peak_memory_bytes: int


_measurement_lock = Lock()


def run_search(problem, algorithm, limits, heuristic=None) -> RunResult:
    board = getattr(getattr(problem, "initial", None), "board", None)
    if board is not None and getattr(board, "splitTargets", {}) and heuristic is not None:
        from search.heuristics import zero
        if heuristic is not zero:
            raise ValueError("Split/teleport heuristic is unverified; use None or search.heuristics.zero")
    if not isinstance(limits, SearchLimits):
        raise TypeError("limits must be SearchLimits")
    if not isfinite(limits.timeout_seconds) or limits.timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive and finite")
    if type(limits.max_expanded_nodes) is not int or limits.max_expanded_nodes < 0:
        raise ValueError("max_expanded_nodes must be a nonnegative integer")
    solver = get_solver(algorithm)
    if not _measurement_lock.acquire(blocking=False):
        raise RuntimeError("Another search measurement is running")
    try:
        if tracemalloc.is_tracing():
            raise RuntimeError("tracemalloc is already active; run measurements separately")
        tracemalloc.start()
        try:
            start = perf_counter()
            result = solver(problem, limits, heuristic)
            elapsed = perf_counter() - start
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        if not isinstance(result, SearchResult):
            raise TypeError("Solver must return SearchResult")
        return RunResult(result, elapsed, peak)
    finally:
        _measurement_lock.release()


def validate_solution(problem, result):
    """Replay a solved result outside solve measurement; return its final state.

    Raises ValueError for false solved results. Non-solved results have no replay.
    Does not mutate problem.initial or silently relabel an invalid solution.
    """
    from math import isclose
    from gameModel.block import Direction
    if result.status != "solved":
        return None
    if not isinstance(result.actions, tuple):
        raise ValueError("Solution actions must be a tuple")
    state = problem.initial.copy()
    cost = 0.0
    for index, action in enumerate(result.actions):
        if not isinstance(action, Direction) or action not in problem.actions(state):
            raise ValueError(f"Invalid solution action at step {index}")
        child = problem.result(state, action)
        if child is None:
            raise ValueError(f"Illegal solution move at step {index}")
        step = problem.step_cost(state, action, child)
        if not isfinite(step) or step <= 0:
            raise ValueError(f"Invalid step cost at step {index}")
        cost += step
        state = child
    if not problem.goal_test(state):
        raise ValueError("Solution does not end at the goal")
    if result.total_cost is None or not isfinite(result.total_cost) or not isclose(cost, result.total_cost, rel_tol=1e-9, abs_tol=1e-9):
        raise ValueError("Solution cost disagrees with replay")
    return state
