from gameModel.block import Direction, Orientation
from gameModel.board import Tile, FRAGILE_PENALTY
from gameModel.rules import transition, winning


class Problem:
    def __init__(self, initialState, *, unit_cost=False, fragile_penalty=FRAGILE_PENALTY):
        self.initial = initialState
        self.unit_cost = unit_cost
        self.fragile_penalty = fragile_penalty


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
        block = nextState.block
        positions = ([block.cubes[block.active]] if block.orientation == Orientation.SPLIT
                     and state.block.orientation == Orientation.SPLIT else block.occupied())
        tiles = [nextState.board.getTile(*p) for p in positions]
        if Tile.VOID in tiles:
            return float('inf')
        return 1.0 + (self.fragile_penalty if Tile.FRAGILE in tiles else 0.0)
