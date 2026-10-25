from gameModel.block import Block
from gameModel.board import Board
from gameModel.state import State
from gameModel.rules import transition, supported, winning, pressed


class GameController:
    def __init__(self, board: Board, initialBlock: Block):
        self.board = board
        self.block = initialBlock
        self.isGameOver = False
        self.hasWon = False

    def reset(self):
        self.board.reset()
        self.block = Block(self.board.startR, self.board.startC)
        self.isGameOver = self.hasWon = False

    def getOccupiedTiles(self, block):
        return block.occupied()

    def isValidBlockPosition(self, block):
        return supported(State(self.board, block))

    def activateSwitches(self):
        # Legacy explicit helper; executeMove uses the shared entry-based rules.
        for position in sorted(pressed(State(self.board, self.block))):
            self.board.applySwitch(position)
        if self.board.fatalSwitch is not None:
            self.isGameOver, self.hasWon = True, False

    def isWinningState(self):
        return winning(State(self.board, self.block))

    def executeMove(self, direction):
        if self.isGameOver or self.hasWon:
            return False
        child, valid, lost = transition(State(self.board, self.block), direction)
        # Preserve board identity for callers holding a reference to the live game.
        self.board.__dict__.update(child.board.__dict__)
        self.block = child.block
        self.isGameOver = lost
        self.hasWon = valid and winning(child)
        return valid

    def completeLevel(self):
        return self.hasWon
