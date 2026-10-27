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
                        Bloxorz (every bridge permanently open, switches do nothing,
                        teleport destinations are free-cost shortcuts).

Fields read: problem.unit_cost, problem.initial.board (tiles, bridgeGroups, rows,
cols, splitTargets), state.block (r, c, dr, dc, orientation, cubes, active).
Nothing is modified.

Why ``relaxed_distance`` is admissible and consistent
-----------------------------------------------------
Let P be the real problem and R the relaxed one. R has the same nodes
(r, c, dr, dc), the same roll geometry (Block.resultingState), the same
out-of-board / VOID / FRAGILE-when-standing rules and the same goal (standing on
GOAL). R differs from P in two ways:

1. Every cell listed in board.bridgeGroups is treated as an always-open BRIDGE tile
   and switches never toggle anything.
2. Standing on a SPLIT_SWITCH cell is additionally connected to each teleport
   destination via a zero-cost edge, allowing instant traversal.

Every legal real move is also a legal relaxed move with the same or higher cost:
bridges that are open in the real game are open in R; a teleport in P requires one
move to the split switch plus landing cost — the relaxed model offers the same
path for free, which is ≤ the real cost. Therefore:
    h(s) = cost_R*(s) ≤ cost_P*(s)  → admissible.
Because h is a true shortest-path distance in a graph R that is a supergraph of P's
edges, h(s) ≤ c(s, s') + h(s') for every R-edge, and so for every real edge
→ consistent. h = 0 on the goal, h ≥ 0 everywhere.

Split states: when the block is split into two cubes, each cube must independently
reach the goal after merging. A safe lower bound is the minimum relaxed distance
among the two cube positions (since one of them could be adjacent to the goal).
This remains admissible because the real cost is at least the cost to reach the
goal with the closer cube.

Dead states: if the goal is unreachable even in R the real state is hopeless too.
We return the finite sentinel DEAD_H. It is admissible (true cost is infinite) and
consistent (dead states form a closed set sharing one value) and keeps the
"finite" requirement of the contract.
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

    # Add zero-cost teleport shortcut edges for split switches.
    # Standing on a SPLIT_SWITCH teleports cubes to distant destinations;
    # in the relaxed model we add a free edge from each destination back to
    # the split switch (backward Dijkstra direction), so any state that can
    # reach a teleport destination is credited for the shortcut.
    split_targets = getattr(board, 'splitTargets', {})
    for switch_pos, destinations in split_targets.items():
        sr, sc = switch_pos
        if tile_at(sr, sc) in (Tile.VOID,):
            continue
        switch_key = (sr, sc, 0, 0)  # standing on the split switch
        for dest_r, dest_c in destinations:
            if tile_at(dest_r, dest_c) == Tile.VOID:
                continue
            dest_key = (dest_r, dest_c, 0, 0)  # standing at destination
            # Backward edge: from destination, you can reach the switch for free.
            # This means: in forward direction, from switch you can reach dest for free.
            reverse[switch_key].append((dest_key, 0.0))

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


def _is_split(block):
    """Check whether the block is in SPLIT orientation (two independent cubes)."""
    return getattr(block, 'orientation', None) == Orientation.SPLIT


def relaxed_distance(problem, state) -> float:
    """Exact cost-to-go on the relaxed problem (admissible and consistent).

    For split states (two cubes), returns the minimum relaxed distance among
    the two cube positions. This is admissible because the real solution must
    move at least one cube to the goal (after merging), and the merge itself
    requires the other cube to be adjacent — making the true cost ≥ the
    minimum single-cube distance.
    """
    block = getattr(state, "block", None)
    if block is None:
        return 0.0  # unsupported state layout: safe fallback

    table = _table(problem)

    if _is_split(block):
        # Two cubes: return min distance among cube positions (standing).
        cubes = getattr(block, 'cubes', ())
        if not cubes:
            return 0.0
        return min(table.get((r, c, 0, 0), DEAD_H) for r, c in cubes)

    if not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0  # missing attributes: safe fallback

    return table.get((block.r, block.c, block.dr, block.dc), DEAD_H)


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


def _teleport_destinations(problem):
    """All teleport destination cells for the problem (cached)."""
    dests = _TELEPORT_DESTS.get(problem)
    if dests is None:
        board = problem.initial.board
        split_targets = getattr(board, 'splitTargets', {})
        dests = []
        for positions in split_targets.values():
            dests.extend(positions)
        _TELEPORT_DESTS[problem] = dests
    return dests


def manhattan_lower_bound(problem, state) -> float:
    """m * max(1, ceil(D / 2)), 0 when standing on the goal.

    D = min Manhattan distance from an occupied cell to a goal cell. One roll lowers D
    by at most 2 (standing -> lying or lying -> standing along an axis) and by at most 1
    otherwise, so at least ceil(D / 2) rolls are needed; when D = 0 but the block is not
    standing on the goal at least one more roll is needed. m is the cheapest possible
    move: 1.0 under unit cost, else min(TILE_COST) = 0.5. Admissible, and consistent
    because ceil(D / 2) drops by at most 1 per roll while every roll costs >= m.

    On levels with teleport (splitTargets), the block may reach the goal through a
    teleport destination. We take the minimum Manhattan distance considering both
    direct paths and paths through any teleport destination, preserving admissibility.

    For split states (two cubes), returns the minimum bound among the two cube
    positions. This is admissible for the same reason as relaxed_distance.
    """
    block = getattr(state, "block", None)
    if block is None:
        return 0.0

    goals = _goal_cells(problem)
    if not goals:
        return 0.0

    per_move = 1.0 if problem.unit_cost else min(TILE_COST.values())

    if _is_split(block):
        cubes = getattr(block, 'cubes', ())
        if not cubes:
            return 0.0
        return min(_manhattan_single(r, c, True, goals, per_move, problem)
                   for r, c in cubes)

    if not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0

    cells = _occupied(block)
    is_standing = block.orientation == Orientation.STANDING

    # Direct distance to goal
    d_direct = min(abs(r - gr) + abs(c - gc) for r, c in cells for gr, gc in goals)
    if d_direct == 0 and is_standing:
        return 0.0

    # Check teleport shortcut: distance to a split switch + distance from
    # teleport destination to goal. Since teleport is a single move, the total
    # lower bound via teleport is: ceil(D_to_switch / 2) + 1 + ceil(D_from_dest / 2).
    # We take the minimum of the direct and all teleport-via paths.
    d = d_direct
    teleport_dests = _teleport_destinations(problem)
    board = problem.initial.board
    split_targets = getattr(board, 'splitTargets', {})
    for switch_pos, destinations in split_targets.items():
        sr, sc = switch_pos
        # Distance from current position to the split switch
        d_to_switch = min(abs(r - sr) + abs(c - sc) for r, c in cells)
        # Best distance from any teleport destination to goal
        d_from_dest = min(abs(dr - gr) + abs(dc - gc)
                          for dr, dc in destinations for gr, gc in goals)
        # Via teleport: moves_to_switch + 1_teleport_move + moves_from_dest_to_goal
        # But we need a lower bound: at minimum ceil(d_to_switch/2) + ceil(d_from_dest/2)
        # (the teleport step itself has cost >= per_move)
        d_via = max(1, -(-d_to_switch // 2)) + max(1, -(-d_from_dest // 2))
        d = min(d, d_via)

    return max(1, -(-d_direct // 2)) * per_move if d == d_direct else d * per_move


def _manhattan_single(r, c, standing, goals, per_move, problem):
    """Manhattan lower bound for a single cube at (r, c)."""
    d = min(abs(r - gr) + abs(c - gc) for gr, gc in goals)
    if d == 0 and standing:
        return 0.0

    board = problem.initial.board
    split_targets = getattr(board, 'splitTargets', {})
    for switch_pos, destinations in split_targets.items():
        sr, sc = switch_pos
        d_to_switch = abs(r - sr) + abs(c - sc)
        d_from_dest = min(abs(dr - gr) + abs(dc - gc)
                          for dr, dc in destinations for gr, gc in goals)
        d_via = max(1, -(-d_to_switch // 2)) + max(1, -(-d_from_dest // 2))
        d = min(d, d_via)

    return max(1, -(-d // 2)) * per_move


HEURISTICS = {
    "zero": zero,
    "manhattan": manhattan_lower_bound,
    "relaxed": relaxed_distance,
}
