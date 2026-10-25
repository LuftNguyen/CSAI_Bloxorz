"""Deterministic, frame-independent transitions shared by search and play.

See docs/GAME_RULES.md for entry activation, ordered effects and teleport policy.
The failed successor is retained for controller fall/break visuals; search discards it.
"""
from gameModel.block import Block, Direction, Orientation
from gameModel.board import Tile


def winning(state):
    b = state.block
    return (state.board.fatalSwitch is None and b.orientation == Orientation.STANDING and b.dr == b.dc == 0
            and state.board.getTile(b.r, b.c) == Tile.GOAL)


def supported(state):
    block, board = state.block, state.board
    positions = block.occupied()
    if len(set(positions)) != len(positions):
        return False
    valid = True
    for r, c in positions:
        tile = board.getTile(r, c)
        if tile == Tile.VOID:
            valid = False
        if tile == Tile.FRAGILE and block.orientation == Orientation.STANDING:
            board.setTile(r, c, Tile.VOID)
            valid = False
    return valid


def pressed(state):
    block, board = state.block, state.board
    full_standing = block.orientation == Orientation.STANDING
    return {p for p in block.occupied()
            if board.getTile(*p) == Tile.SOFT_SWITCH or (
                full_standing and board.getTile(*p) in (Tile.HEAVY_SWITCH, Tile.SPLIT_SWITCH))}


def transition(state, action):
    """Return (isolated successor, valid, loss). SWITCH has no tile interactions."""
    child = state.copy()
    if state.board.fatalSwitch is not None:
        return child, False, True
    if not isinstance(action, Direction) or (action == Direction.SWITCH and
                                            state.block.orientation != Orientation.SPLIT):
        return child, False, False
    child.block = child.block.resultingState(action)
    if action == Direction.SWITCH:
        valid = supported(child)
        return child, valid, not valid
    if not supported(child):
        return child, False, True
    activated = pressed(child) - pressed(state)
    for position in sorted(activated):
        child.board.applySwitch(position)
        if child.board.fatalSwitch is not None:
            return child, False, True
    if not supported(child):
        return child, False, True
    b = child.block
    position = (b.r, b.c)
    if b.orientation == Orientation.STANDING and position in activated and position in child.board.splitTargets:
        child.block = Block.split(child.board.splitTargets[position])
        if not supported(child):
            return child, False, True
        if position in child.board.fatalSplitSwitches:
            child.board.fatalSwitch = position
            return child, False, True
        # Arrival presses soft switches once. Cubes cannot trigger heavy/split.
        for destination in sorted(pressed(child)):
            child.board.applySwitch(destination)
            if child.board.fatalSwitch is not None:
                return child, False, True
        if not supported(child):
            return child, False, True
    b = child.block
    if b.orientation == Orientation.SPLIT:
        (r1, c1), (r2, c2) = b.cubes
        if abs(r1-r2) + abs(c1-c2) == 1:
            child.block = Block(min(r1,r2), min(c1,c2), int(r1!=r2), int(c1!=c2), Orientation.LYING)
    if not supported(child):
        return child, False, True
    return child, True, False
