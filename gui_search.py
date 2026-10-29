"""Cancellable searches, isolated from the render thread and serialized for tracing."""
from concurrent.futures import CancelledError, ThreadPoolExecutor
from threading import Event

from gameModel.problem import Problem
from runner import validate_solution
from search.contracts import SearchLimits


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='bloxorz-search')


class SearchJob(Problem):
    def __init__(self, problem, algorithm, run_search):
        super().__init__(problem.initial, unit_cost=problem.unit_cost)
        self.cancelled = Event()
        self.future = _executor.submit(self.compute, algorithm, run_search)

    def checkpoint(self):
        if self.cancelled.is_set():
            raise CancelledError()

    def goal_test(self, state):
        self.checkpoint()
        return super().goal_test(state)

    def actions(self, state):
        self.checkpoint()
        return super().actions(state)

    def result(self, state, action):
        self.checkpoint()
        return super().result(state, action)

    def compute(self, algorithm, run_search):
        self.checkpoint()
        result = run_search(self, algorithm, SearchLimits(), heuristic=None)
        validate_solution(self, result.search)
        self.checkpoint()
        return result

    def cancel(self):
        self.cancelled.set()
        self.future.cancel()
