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
