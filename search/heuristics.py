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

HEURISTICS = {
    "zero": zero,
    "manhattan": manhattan_lower_bound,
    "relaxed": relaxed_distance,
}
