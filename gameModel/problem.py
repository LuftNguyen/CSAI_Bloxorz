from gameModel.state import State
from gameModel.block import Direction, Orientation
from gameModel.board import Tile, TILE_COST


class Problem:

    def __init__(self, initialState, *, unit_cost=False):
        self.initial = initialState
        self.unit_cost = unit_cost

    def goal_test(self, state):

        block = state.block

        return (
            block.orientation == Orientation.STANDING
            and block.dr == 0 and block.dc == 0
            and state.board.getTile(block.r, block.c) == Tile.GOAL
        )

    def actions(self, state):
        return list(Direction)

    def result(self, state, action):

        nextState = state.copy()

        nextBlock = nextState.block.resultingState(action)
        nextState.block = nextBlock

        # Các ô block đang chiếm
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

        for r, c in occupied:

            tile = nextState.board.getTile(r, c)

            if tile == Tile.SOFT_SWITCH:

                nextState.board.toggleBridge((r, c))

            elif (
                tile == Tile.HEAVY_SWITCH
                and nextBlock.orientation == Orientation.STANDING
            ):

                nextState.board.toggleBridge((r, c))

        for r, c in occupied:

            tile = nextState.board.getTile(r, c)

            if tile == Tile.VOID:
                return None

            if (
                tile == Tile.FRAGILE
                and nextBlock.orientation == Orientation.STANDING
            ):
                return None

        return nextState

    def step_cost(self, state, action, nextState):

        if self.unit_cost:
            return 1.0

        block = nextState.block

        tiles = [
            nextState.board.getTile(
                block.r,
                block.c
            )
        ]

        if block.dr == 1:

            tiles.append(
                nextState.board.getTile(
                    block.r + 1,
                    block.c
                )
            )

        elif block.dc == 1:

            tiles.append(
                nextState.board.getTile(
                    block.r,
                    block.c + 1
                )
            )

        if any(tile == Tile.VOID for tile in tiles):
            return float("inf")

        return max(
            TILE_COST[t]
            for t in tiles
        )
