from gameModel.block import Direction, Orientation
from gameModel.board import Tile, TILE_COST
from gameModel.rules import transition, winning


class Problem:
    def __init__(self, initialState, *, unit_cost=False):
        self.initial = initialState
        self.unit_cost = unit_cost

    def goal_test(self, state):
        return winning(state)

    def actions(self, state):
        return [a for a in Direction if a != Direction.SWITCH or state.block.orientation == Orientation.SPLIT]

    def result(self, state, action):
        child, valid, _ = transition(state, action)
        return child if valid else None

    def step_cost(self, state, action, nextState):
        if self.unit_cost or action == Direction.SWITCH:
            return 1.0
        # Preserve source max landing-tile cost. A cube move charges its landing
        # tile; teleport/merge charges the resulting occupied cells.
        block = nextState.block
        positions = ([block.cubes[block.active]] if block.orientation == Orientation.SPLIT
                     and state.block.orientation == Orientation.SPLIT else block.occupied())
        tiles = [nextState.board.getTile(*p) for p in positions]
        if Tile.VOID in tiles:
            return float('inf')
        return float(max(TILE_COST[t] for t in tiles))
