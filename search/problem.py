from gameModel.state import State
from gameModel.block import Direction, Orientation
from gameModel.board import Tile


class Problem:

    def __init__(self, initialState):

        self.initial = initialState

    def goal_test(self, state):

        block = state.block

        return (
            block.orientation == Orientation.STANDING
            and
            state.board.getTile(block.r, block.c) == Tile.GOAL
        )

    def actions(self, state):

        return list(Direction)

    def result(self, state, action):

        nextState = state.copy()

        nextBlock = nextState.block.resultingState(action)

        nextState.block = nextBlock

        occupied = [(nextBlock.r, nextBlock.c)]

        if nextBlock.dr == 1:
            occupied.append((nextBlock.r + 1, nextBlock.c))

        elif nextBlock.dc == 1:
            occupied.append((nextBlock.r, nextBlock.c + 1))

        for r, c in occupied:

            tile = nextState.board.getTile(r, c)

            if tile == Tile.VOID:
                return None

            if (
                tile == Tile.FRAGILE
                and nextBlock.orientation == Orientation.STANDING
            ):
                return None

        tile = nextState.board.getTile(nextBlock.r, nextBlock.c)

        if tile == Tile.SOFT_SWITCH:

            nextState.board.toggleBridge(
                nextBlock.r,
                nextBlock.c
            )

        elif (
            tile == Tile.HEAVY_SWITCH
            and nextBlock.orientation == Orientation.STANDING
        ):

            nextState.board.toggleBridge(
                nextBlock.r,
                nextBlock.c
            )

        return nextState

    def step_cost(self, state, action, nextState):
        return 1.0