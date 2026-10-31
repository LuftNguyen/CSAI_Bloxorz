from collections import defaultdict
from heapq import heappop, heappush
from itertools import count
from weakref import WeakKeyDictionary

from gameModel.block import Block, Direction, Orientation
from gameModel.board import Tile

DEAD_H = 1.0e9  # finite stand-in for "goal unreachable"

# Only roll directions for the relaxed block graph; SWITCH is handled separately.
_ROLL_DIRS = tuple(d for d in Direction if d != Direction.SWITCH)

# problem -> {(r, c, dr, dc): cost-to-go}; weak keys so tables die with the problem.
_TABLES = WeakKeyDictionary()
_GOALS = WeakKeyDictionary()
_TELEPORT_DESTS = WeakKeyDictionary()


def zero(problem, state) -> float:
    return 0.0


# Relaxed model
def _static_tile_map(board):
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
    board = problem.initial.board
    tiles = _static_tile_map(board)
    rows, cols = board.rows, board.cols

    def tile_at(r, c):
        if 0 <= r < rows and 0 <= c < cols:
            return tiles[r][c]
        return Tile.VOID

    def landing_cost(block):
        has_fragile = False
        for r, c in _occupied(block):
            tile = tile_at(r, c)
            if tile == Tile.VOID:
                return None
            if tile == Tile.FRAGILE and block.orientation == Orientation.STANDING:
                return None
            if tile == Tile.FRAGILE:
                has_fragile = True
        if problem.unit_cost:
            return 1.0
        return 1.0 + (problem.fragile_penalty if has_fragile else 0.0)

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
    _table(problem)


def _is_split(block):
    return getattr(block, 'orientation', None) == Orientation.SPLIT


def relaxed_distance(problem, state) -> float:
    block = getattr(state, "block", None)
    if block is None or _is_split(block):
        return 0.0
    if not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0  # unsupported state layout: safe fallback
    return _table(problem).get((block.r, block.c, block.dr, block.dc), DEAD_H)


# Closed-form bound (comparison baseline for the report)
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
    block = getattr(state, "block", None)
    if block is None or _is_split(block):
        return 0.0
    if not all(hasattr(block, a) for a in ("r", "c", "dr", "dc")):
        return 0.0
    goals = _goal_cells(problem)
    if not goals:
        return 0.0
    per_move = 1.0
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


# ---------------------------------------------------------------------------
# Projection heuristic that also covers the split phase ("relaxed_split").
#
# Relaxation R = the real problem with the bridge/switch variables projected
# away:  every bridge cell is permanently open and switches have no effect.
# Everything else is kept *exactly*: roll geometry, fragile rule, goal rule,
# teleport at split switches, two cubes + which one is active, SWITCH action,
# automatic merge of two adjacent cubes, step costs.
#
#   * every real transition (s -> s', c) maps to an R transition with the same
#     cost, so d_R(.) <= d_real(.)                    -> admissible
#   * h = d_R(., goal) is a shortest-path distance in R, so
#     h(s) <= c(s,s') + h(s') on every R edge (hence every real edge)
#                                                      -> consistent
# R keeps both full-block keys (r, c, dr, dc) and split keys
# (r0, c0, r1, c1, active); only states reachable in R from problem.initial
# are enumerated, then one backward Dijkstra from the goal fills the table.
# Lookup is O(1), including while the block is split.
# ---------------------------------------------------------------------------
_SPLIT_TABLES = WeakKeyDictionary()
_STEPS = ((-1, 0), (1, 0), (0, -1), (0, 1))


def _state_key(block):
    if block.orientation == Orientation.SPLIT:
        (r0, c0), (r1, c1) = block.cubes
        return (r0, c0, r1, c1, block.active)
    return (block.r, block.c, block.dr, block.dc)


def _build_split_table(problem):
    state0 = problem.initial
    board = state0.board
    tiles = _static_tile_map(board)
    rows, cols = board.rows, board.cols
    unit, lam = problem.unit_cost, problem.fragile_penalty
    targets = dict(getattr(board, "splitTargets", {}))
    fatal_split = set(getattr(board, "fatalSplitSwitches", ()))
    fatal_close = set(getattr(board, "fatalCloseSwitches", ()))
    # A fatal soft switch can never be touched by any piece and a fatal heavy
    # switch never be stood on by a full block (real moves there are losses).
    fatal_soft = {p for p in fatal_close if tiles[p[0]][p[1]] == Tile.SOFT_SWITCH}
    fatal_heavy = {p for p in fatal_close if tiles[p[0]][p[1]] == Tile.HEAVY_SWITCH}

    def floor(r, c):
        return (0 <= r < rows and 0 <= c < cols and tiles[r][c] != Tile.VOID
                and (r, c) not in fatal_soft)

    def standable(r, c):
        return (floor(r, c) and tiles[r][c] != Tile.FRAGILE
                and (r, c) not in fatal_heavy and (r, c) not in fatal_split)

    def cost(cells):
        if unit:
            return 1.0
        return 1.0 + (lam if any(tiles[r][c] == Tile.FRAGILE for r, c in cells) else 0.0)

    def lying_key(p, q):
        return (min(p[0], q[0]), min(p[1], q[1]), int(p[0] != q[0]), int(p[1] != q[1]))

    def teleport(cell):
        t0, t1 = targets[cell]
        if not (floor(*t0) and floor(*t1)):
            return None
        c = cost((t0, t1))
        if abs(t0[0] - t1[0]) + abs(t0[1] - t1[1]) == 1:  # adjacent targets merge at once
            return lying_key(t0, t1), c
        return (t0[0], t0[1], t1[0], t1[1], 0), c

    def successors(key):
        out = []
        if len(key) == 5:  # split: one cube moves, or control is handed over
            r0, c0, r1, c1, k = key
            cubes = [(r0, c0), (r1, c1)]
            moving, other = cubes[k], cubes[1 - k]
            out.append(((r0, c0, r1, c1, 1 - k), 1.0))  # SWITCH
            for dr, dc in _STEPS:
                q = (moving[0] + dr, moving[1] + dc)
                if q == other or not floor(*q):
                    continue
                if abs(q[0] - other[0]) + abs(q[1] - other[1]) == 1:
                    out.append((lying_key(q, other), cost((q, other))))
                else:
                    new = list(cubes)
                    new[k] = q
                    out.append(((new[0][0], new[0][1], new[1][0], new[1][1], k), cost((q,))))
            return out
        r, c, dr, dc = key
        orient = (Orientation.STANDING if not (dr or dc) else Orientation.LYING)
        block = Block(r, c, dr, dc, orient)
        for direction in _ROLL_DIRS:
            nb = block.resultingState(direction)
            cells = nb.occupied()
            if not all(floor(*p) for p in cells):
                continue
            if nb.orientation == Orientation.STANDING:
                if not standable(nb.r, nb.c):
                    continue
                if (nb.r, nb.c) in targets:
                    hop = teleport((nb.r, nb.c))
                    if hop is not None:
                        out.append(hop)
                    continue
                out.append(((nb.r, nb.c, 0, 0), cost(cells)))
            else:
                out.append(((nb.r, nb.c, nb.dr, nb.dc), cost(cells)))
        return out

    goals = {(r, c, 0, 0) for r in range(rows) for c in range(cols) if tiles[r][c] == Tile.GOAL}
    start = _state_key(state0.block)
    reverse, seen, stack = defaultdict(list), {start}, [start]
    while stack:
        key = stack.pop()
        if key in goals:  # search stops at the goal; never expand past it
            continue
        for nxt, c in successors(key):
            reverse[nxt].append((key, c))
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)

    dist, heap, tie = {}, [], count()
    for g in goals & seen:
        dist[g] = 0.0
        heappush(heap, (0.0, next(tie), g))
    while heap:
        d, _, node = heappop(heap)
        if d > dist.get(node, float("inf")):
            continue
        for prev, c in reverse.get(node, ()):
            nd = d + c
            if nd < dist.get(prev, float("inf")):
                dist[prev] = nd
                heappush(heap, (nd, next(tie), prev))
    return {key: dist.get(key, DEAD_H) for key in seen}


def _split_table(problem):
    table = _SPLIT_TABLES.get(problem)
    if table is None:
        table = _build_split_table(problem)
        _SPLIT_TABLES[problem] = table
    return table


def precompute_split(problem) -> None:
    _split_table(problem)


def relaxed_split_distance(problem, state) -> float:
    block = getattr(state, "block", None)
    if block is None or not all(hasattr(block, a) for a in ("r", "c", "dr", "dc", "orientation")):
        return 0.0  # unsupported layout: safe fallback
    return _split_table(problem).get(_state_key(block), 0.0)

HEURISTICS = {
    "zero": zero,
    "manhattan": manhattan_lower_bound,
    "relaxed": relaxed_distance,
    "relaxed_split": relaxed_split_distance,
}