from copy import deepcopy

from gameModel.block import Block
from gameModel.board import Board, Tile


class State:
    """
    Search state = Block + current bridge status.
    """

    def __init__(self, board: Board, block: Block):

        self.board = board
        self.block = block.copy()

    def copy(self):
        return State(
            deepcopy(self.board),
            self.block.copy()
        )

    def __eq__(self, other):
        return (
            isinstance(other, State)
            and
            self.block == other.block
            and
            self.board.tiles == other.board.tiles
            and self.board.bridgeState == other.board.bridgeState
            and self.board.bridgeGroups == other.board.bridgeGroups
            and self.board.switchEffects == other.board.switchEffects
            and self.board.splitTargets == other.board.splitTargets
            and self.board.fatalCloseSwitches == other.board.fatalCloseSwitches
            and self.board.fatalSplitSwitches == other.board.fatalSplitSwitches
            and self.board.fatalSwitch == other.board.fatalSwitch
            and (self.board.rows, self.board.cols) == (other.board.rows, other.board.cols)
        )

    def __hash__(self):

        boardState = tuple(tuple(r) for r in self.board.tiles)

        return hash(
            (
                self.block,
                boardState,
                self.board.rows,
                self.board.cols,
                frozenset(self.board.bridgeState.items()),
                self.board.rules_key(),
                self.board.fatalSwitch,
            )
        )

    def __repr__(self):

        return f"State({self.block})"
