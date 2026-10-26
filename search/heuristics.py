"""Person 5: implement and verify heuristics; compare A* with h=0 against UCS.

Values must be finite, nonnegative and zero at goals. Revalidate admissibility
after teleport or cost changes. Upstream Manhattan is an unverified reference.
"""


"""Heuristics for A* (heuristic owner: Huong).

Every heuristic has the contract signature ``heuristic(problem, state) -> float``:
finite, non-negative, 0 at the goal, no side effects, no GUI access.

Provided heuristics
-------------------
zero                    h = 0 (baseline; A* then behaves like UCS).
manhattan_lower_bound   closed form, O(1) per call, loose but easy to prove.
relaxed_distance        MAIN heuristic: exact shortest-path cost-to-go on a *relaxed*
                        Bloxorz (every bridge permanently open, switches do nothing).

Fields read: problem.unit_cost, problem.initial.board (tiles, bridgeGroups, rows,
cols), state.block (r, c, dr, dc, orientation). Nothing is modified.

Why ``relaxed_distance`` is admissible and consistent
-----------------------------------------------------
Let P be the real problem and R the relaxed one. R has the same nodes
(r, c, dr, dc), the same roll geometry (Block.resultingState), the same
out-of-board / VOID / FRAGILE-when-standing rules and the same goal (standing on
GOAL). R differs from P only in that every cell listed in board.bridgeGroups is
treated as an always-open BRIDGE tile and switches never toggle anything. The edge
cost in R is the real Problem.step_cost formula (max TILE_COST over the occupied
cells, or 1.0 when problem.unit_cost).

Every legal real move is also a legal relaxed move with the same cost: a legal real
move never occupies a VOID cell, a closed bridge is VOID (so it is never occupied
after a legal move) and an open bridge costs TILE_COST[BRIDGE], exactly what R uses.
Therefore h(s) = cost_R*(s) <= cost_P*(s)  -> admissible. Because h is a true
shortest-path distance in R, h(s) <= c(s, s') + h(s') for every R-edge, and so for
every real edge -> consistent. h = 0 on the goal, h >= 0 everywhere.

Dead states: if the goal is unreachable even in R the real state is hopeless too.
We return the finite sentinel DEAD_H. It is admissible (true cost is infinite) and
consistent (dead states form a closed set sharing one value) and keeps the
"finite" requirement of the contract.

Unsupported rules: the engine currently has no split/teleport/SWITCH action. If a
state has no plain ``block`` with r/c/dr/dc (e.g. a future split state),
relaxed_distance returns 0.0, the contract's safe fallback. Re-validate after any
cost or rule change; tests/test_heuristics.py checks admissibility and consistency
against exact optimal costs on the real levels.
"""
from collections import defaultdict
from heapq import heappop, heappush
from itertools import count
from weakref import WeakKeyDictionary

from gameModel.block import Block, Direction, Orientation
from gameModel.board import TILE_COST, Tile

DEAD_H = 1.0e9  # finite stand-in for "goal unreachable"

# problem -> {(r, c, dr, dc): cost-to-go}; weak keys so tables die with the problem.
_TABLES = WeakKeyDictionary()
_GOALS = WeakKeyDictionary()


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
    cells = [(block.r, block.c)]
    if block.dr == 1:
        cells.append((block.r + 1, block.c))
    elif block.dc == 1:
        cells.append((block.r, block.c + 1))
    return cells


def _build_table(problem):
    """Backward Dijkstra from every GOAL cell over the relaxed block graph."""
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
                for direction in Direction:
                    nxt = block.resultingState(direction)
                    cost = landing_cost(nxt)
                    if cost is not None:
                        reverse[key(nxt)].append((key(block), cost))

    dist, heap, tie = {}, [], count()
    for r in range(rows):
        for c in range(cols):
            if tiles[r][c] == Tile.GOAL:
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


def relaxed_distance(problem, state) -> float:
    """Exact cost-to-go on the relaxed problem (admissible and consistent)."""
    block = getattr(state, "block", None)
    if block is None or not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0  # unsupported state layout (e.g. split blocks): safe fallback
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


def manhattan_lower_bound(problem, state) -> float:
    """m * max(1, ceil(D / 2)), 0 when standing on the goal.

    D = min Manhattan distance from an occupied cell to a goal cell. One roll lowers D
    by at most 2 (standing -> lying or lying -> standing along an axis) and by at most 1
    otherwise, so at least ceil(D / 2) rolls are needed; when D = 0 but the block is not
    standing on the goal at least one more roll is needed. m is the cheapest possible
    move: 1.0 under unit cost, else min(TILE_COST) = 0.5. Admissible, and consistent
    because ceil(D / 2) drops by at most 1 per roll while every roll costs >= m.
    """
    block = getattr(state, "block", None)
    if block is None or not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0
    goals = _goal_cells(problem)
    if not goals:
        return 0.0
    cells = _occupied(block)
    d = min(abs(r - gr) + abs(c - gc) for r, c in cells for gr, gc in goals)
    if d == 0 and block.orientation == Orientation.STANDING:
        return 0.0
    per_move = 1.0 if problem.unit_cost else min(TILE_COST.values())
    return max(1, -(-d // 2)) * per_move


HEURISTICS = {
    "zero": zero,
    "manhattan": manhattan_lower_bound,
    "relaxed": relaxed_distance,
}
