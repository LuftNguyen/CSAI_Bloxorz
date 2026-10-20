from gameModel.block import *
from gameModel.board import *


class GameController:
    def __init__(self, board: Board, initialBlock: Block):
        self.board = board
        self.block = initialBlock
        self.isGameOver = False
        self.hasWon = False

    def reset(self):
        """Resets the game state and board back to level start."""
        self.board.reset()

        self.block = Block(
            self.board.startR,
            self.board.startC,
            0,
            0,
            Orientation.STANDING
        )

        self.isGameOver = False
        self.hasWon = False

    def getOccupiedTiles(self, block: Block):
        tiles = [(block.r, block.c)]

        if block.dr == 1:
            tiles.append((block.r + 1, block.c))

        elif block.dc == 1:
            tiles.append((block.r, block.c + 1))

        return tiles

    def isValidBlockPosition(self, block: Block):

        for r, c in self.getOccupiedTiles(block):

            tile = self.board.getTile(r, c)

            # Block falls
            if tile == Tile.VOID:
                return False

            # Fragile tile breaks when standing upright
            if (
                tile == Tile.FRAGILE
                and block.orientation == Orientation.STANDING
            ):
                self.board.setTile(r, c, Tile.VOID)
                return False

        return True

    def activateSwitches(self):
        occupied = self.getOccupiedTiles(self.block)

        for r, c in occupied:

            tile = self.board.getTile(r, c)

            # Soft switch
            if tile == Tile.SOFT_SWITCH:
                self.board.toggleBridge((r, c))

            # Heavy switch
            if (
                tile == Tile.HEAVY_SWITCH
                and self.block.orientation == Orientation.STANDING
            ):
                self.board.toggleBridge((r, c))

    def isWinningState(self):
        return (
            self.block.orientation == Orientation.STANDING
            and self.block.dr == 0 and self.block.dc == 0
            and self.board.getTile(
                self.block.r,
                self.block.c
            ) == Tile.GOAL
        )

    def executeMove(self, direction: Direction):

        if self.isGameOver or self.hasWon:
            return False

        self.block.applyMove(direction)

        if not self.isValidBlockPosition(self.block):
            self.isGameOver = True
            return False

        # Activate buttons after moving
        self.activateSwitches()

        # A switch may remove support under the block, as in Problem.result().
        if not self.isValidBlockPosition(self.block):
            self.isGameOver = True
            return False

        if self.isWinningState():
            self.hasWon = True

        return True
    
    def completeLevel(self):

        if self.hasWon:
            return True

        return False
