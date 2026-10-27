"""Heuristics for A* (heuristic owner: Huong).

Every heuristic has the contract signature ``heuristic(problem, state) -> float``:
finite, non-negative, 0 at the goal, no side effects, no GUI access.

Provided heuristics
-------------------
zero                    h = 0 (baseline; A* then behaves like UCS).
manhattan_lower_bound   closed form, O(1) per call, loose but easy to prove.
relaxed_distance        MAIN heuristic: exact shortest-path cost-to-go on a *relaxed*
                        Bloxorz (every bridge permanently open, switches do nothing,
                        every split switch is a zero-cost target).

Fields read: problem.unit_cost, problem.initial.board (tiles, bridgeGroups, rows,
cols, splitTargets), state.block (r, c, dr, dc, orientation). Nothing is modified.

Why ``relaxed_distance`` is admissible and consistent
-----------------------------------------------------
Let P be the real problem and R the relaxed one. R has the same nodes
(r, c, dr, dc), the same roll geometry (Block.resultingState), the same
out-of-board / VOID / FRAGILE-when-standing rules and the same edge costs. R differs
from P in two ways:

1. Every cell in board.bridgeGroups is an always-open BRIDGE tile; switches never
   toggle anything.
2. The cost-to-go of a block standing on a SPLIT_SWITCH cell is 0 (it is a target
   of the backward Dijkstra, like GOAL).

Every real plan that does not use a split switch is a path in R to a GOAL, so
h(s) <= h*(s). A plan that uses one must stand on a split switch, which R reaches
with the same or lower cost and then charges 0 for the rest. Hence h is admissible.
h is a shortest-path distance in R, so h(s) <= c(s, s') + h(s') on every R-edge, and
therefore on every real edge between non-split states.

Split states (two cubes) return 0.0, which is admissible. The edge that enters a
split state (rolling onto a split switch) is consistent because the pre-state is at
most one roll (cost >= TILE_COST[SPLIT_SWITCH]) from a zero-cost target:
h(s) <= c + 0. All edges between split states or from split to merged blocks satisfy
0 <= c + h(s') since h >= 0.

Dead states: if no target is reachable even in R the real state is hopeless too.
We return the finite sentinel DEAD_H. It is admissible (true cost is infinite) and
consistent (dead states form a closed set sharing one value) and keeps the
"finite" requirement of the contract.

Re-validate after any cost or rule change; tests/test_heuristics.py checks
admissibility and consistency against exact optimal costs on the real levels.
"""

from collections import defaultdict
from heapq import heappop, heappush
from itertools import count
from weakref import WeakKeyDictionary

from gameModel.block import Block, Direction, Orientation
from gameModel.board import TILE_COST, Tile

DEAD_H = 1.0e9  # finite stand-in for "goal unreachable"

# Only roll directions for the relaxed block graph; SWITCH is handled separately.
_ROLL_DIRS = tuple(d for d in Direction if d != Direction.SWITCH)

# problem -> {(r, c, dr, dc): cost-to-go}; weak keys so tables die with the problem.
_TABLES = WeakKeyDictionary()
_GOALS = WeakKeyDictionary()
_TELEPORT_DESTS = WeakKeyDictionary()


def zero(problem, state) -> float:
    """Contract baseline for UCS/A* integration; no domain heuristic."""
    return 0.0


# ---------------------------------------------------------------------------
# Relaxed model
# ---------------------------------------------------------------------------
def _static_tile_map(board):
    """Terrain with every bridge cell treated as an open BRIDGE tile."""
    tiles = [list(row) for row in board.tiles]
    for cells in board.bridgeGroups.values():
        for r, c in cells:
            if 0 <= r < board.rows and 0 <= c < board.cols:
                tiles[r][c] = Tile.BRIDGE
    return tiles


def _occupied(block):
    """Cells occupied by a non-split block (r, c, dr, dc)."""
    cells = [(block.r, block.c)]
    if block.dr == 1:
        cells.append((block.r + 1, block.c))
    elif block.dc == 1:
        cells.append((block.r, block.c + 1))
    return cells


def _build_table(problem):
    """Backward Dijkstra from every GOAL cell over the relaxed block graph.

    The relaxed graph includes:
    - All 4-direction roll edges for standing/lying blocks.
    - Zero-cost teleport shortcut edges from each SPLIT_SWITCH cell (standing)
      to each teleport destination (standing on that cell), so the heuristic
      accounts for the "warp" effect and stays admissible.
    """
    board = problem.initial.board
    tiles = _static_tile_map(board)
    rows, cols = board.rows, board.cols

    def tile_at(r, c):
        if 0 <= r < rows and 0 <= c < cols:
            return tiles[r][c]
        return Tile.VOID

    def landing_cost(block):
        """Relaxed cost of landing on `block`, or None if the landing is illegal."""
        worst = 0
        for r, c in _occupied(block):
            tile = tile_at(r, c)
            if tile == Tile.VOID:
                return None
            if tile == Tile.FRAGILE and block.orientation == Orientation.STANDING:
                return None
            worst = max(worst, TILE_COST[tile])
        return 1.0 if problem.unit_cost else float(worst)

    def key(b):
        return (b.r, b.c, b.dr, b.dc)

    reverse = defaultdict(list)  # key(next) -> [(key(prev), cost)]
    for r in range(rows):
        for c in range(cols):
            for block in (
                Block(r, c),
                Block(r, c, 0, 1, Orientation.LYING),
                Block(r, c, 1, 0, Orientation.LYING),
            ):
                if landing_cost(block) is None:  # cannot rest here
                    continue
                for direction in _ROLL_DIRS:
                    nxt = block.resultingState(direction)
                    cost = landing_cost(nxt)
                    if cost is not None:
                        reverse[key(nxt)].append((key(block), cost))

    split_cells = set(getattr(board, "splitTargets", {}))
    dist, heap, tie = {}, [], count()
    for r in range(rows):
        for c in range(cols):
            if tiles[r][c] == Tile.GOAL or (r, c) in split_cells:
                dist[(r, c, 0, 0)] = 0.0
                heappush(heap, (0.0, next(tie), (r, c, 0, 0)))

    while heap:
        d, _, node = heappop(heap)
        if d > dist.get(node, float("inf")):
            continue
        for prev, cost in reverse.get(node, ()):
            nd = d + cost
            if nd < dist.get(prev, float("inf")):
                dist[prev] = nd
                heappush(heap, (nd, next(tie), prev))
    return dist


def _table(problem):
    table = _TABLES.get(problem)
    if table is None:
        table = _build_table(problem)
        _TABLES[problem] = table
    return table


def precompute(problem) -> None:
    """Build the lookup table up front (call before timing a solver run)."""
    _table(problem)


def _is_split(block):
    """Check whether the block is in SPLIT orientation (two independent cubes)."""
    return getattr(block, 'orientation', None) == Orientation.SPLIT


def relaxed_distance(problem, state) -> float:
    """Exact cost-to-go on the relaxed problem (admissible and consistent).

    Split states (two cubes) return 0.0: a safe lower bound, and consistent with
    the table, because every split switch is a zero-cost source in the table.
    """
    block = getattr(state, "block", None)
    if block is None or _is_split(block):
        return 0.0
    if not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0  # unsupported state layout: safe fallback
    return _table(problem).get((block.r, block.c, block.dr, block.dc), DEAD_H)


# ---------------------------------------------------------------------------
# Closed-form bound (comparison baseline for the report)
# ---------------------------------------------------------------------------
def _goal_cells(problem):
    cells = _GOALS.get(problem)
    if cells is None:
        board = problem.initial.board
        cells = [
            (r, c)
            for r in range(board.rows)
            for c in range(board.cols)
            if board.tiles[r][c] == Tile.GOAL
        ]
        _GOALS[problem] = cells
    return cells


def _split_cells(problem):
    """Cells of all split switches (cached)."""
    cells = _TELEPORT_DESTS.get(problem)
    if cells is None:
        cells = list(getattr(problem.initial.board, "splitTargets", {}))
        _TELEPORT_DESTS[problem] = cells
    return cells


def manhattan_lower_bound(problem, state) -> float:
    """min(h_goal, h_switch), each of the form m * ceil(D / 2).

    h_goal: D = min Manhattan distance from an occupied cell to a goal cell; 0 when
    standing on the goal, else at least one roll.
    h_switch: same formula towards the nearest split switch (0 when standing on it).
    Any real plan either reaches the goal directly or first stands on a split switch,
    so the min of the two is admissible. Both are consistent, hence so is the min.
    Split states return 0.0.
    """
    block = getattr(state, "block", None)
    if block is None or _is_split(block):
        return 0.0
    if not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0
    goals = _goal_cells(problem)
    if not goals:
        return 0.0
    per_move = 1.0 if problem.unit_cost else min(TILE_COST.values())
    cells = _occupied(block)
    standing = block.orientation == Orientation.STANDING

    def bound(targets):
        d = min(abs(r - tr) + abs(c - tc) for r, c in cells for tr, tc in targets)
        if d == 0 and standing:
            return 0.0
        return max(1, -(-d // 2)) * per_move

    best = bound(goals)
    switches = _split_cells(problem)
    if switches:
        best = min(best, bound(switches))
    return best

HEURISTICS = {
    "zero": zero,
    "manhattan": manhattan_lower_bound,
    "relaxed": relaxed_distance,
}
