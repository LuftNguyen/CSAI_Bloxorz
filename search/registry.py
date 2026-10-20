"""Team solvers only. Never fall back to the source solver."""
from search import bfs, dfs, ucs, astar

SOLVERS = {"bfs": bfs.solve, "dfs": dfs.solve, "ucs": ucs.solve, "astar": astar.solve}


def get_solver(algorithm):
    key = algorithm.strip().lower()
    if key == "a*":
        key = "astar"
    try:
        return SOLVERS[key]
    except KeyError:
        raise ValueError(f"Unknown algorithm: {algorithm!r}; choose {tuple(SOLVERS)}") from None
