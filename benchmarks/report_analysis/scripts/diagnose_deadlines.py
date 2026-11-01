"""Deterministic deadline-policy diagnostic; no sleeping or production edits."""
from common import BASE, write_json
from unittest.mock import Mock, patch
from gameModel.block import Direction
from search import bfs, dfs, ucs, astar
from search.contracts import SearchLimits


def main():
    observations=[]
    for name, module in [('bfs',bfs),('dfs',dfs),('ucs',ucs),('astar',astar)]:
        clock=Mock(return_value=0.)

        class DelayedGoal:
            initial='S'
            def goal_test(self,state):return state=='G'
            def actions(self,state):return [Direction.RIGHT] if state=='S' else []
            def result(self,state,action):
                clock.return_value=2.
                return 'G'
            def step_cost(self,state,action,child):return 1.

        with patch(f'search.{name}.perf_counter',clock):
            r=module.solve(DelayedGoal(),SearchLimits(timeout_seconds=1.))
        observations.append({'algorithm':name,'status':r.status,'expanded':r.expanded_nodes,
                             'generated':r.generated_nodes,'total_cost':r.total_cost})
    write_json(BASE/'metadata/deadline_diagnostic.json',{
        'fixture':'One valid goal successor; fake perf_counter changes from 0s to 2s inside result(); budget=1s.',
        'observations':observations,'consistent_across_solvers':len({r['status'] for r in observations})==1,
        'classification':'Known deadline-boundary policy difference; not a failed campaign replay, not included in benchmark statistics.',
        'production_changed':False})
    print(observations)


if __name__=='__main__':main()
