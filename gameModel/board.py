from enum import Enum
from typing import List


class Tile(Enum):
    VOID = 0
    GOAL = 1
    NORMAL = 2
    FRAGILE = 3
    SOFT_SWITCH = 4
    HEAVY_SWITCH = 5
    BRIDGE = 6

#costs for each tile type, used in uniform cost search
TILE_COST = {

    Tile.NORMAL: 1,

    Tile.GOAL: 1,

    Tile.SOFT_SWITCH: 0.5,

    Tile.HEAVY_SWITCH: 0.5,

    Tile.BRIDGE: 1,

    Tile.FRAGILE: 5
}

#add switch toggles and bridge tiles to the board class, and add a method to toggle switches and bridges
class Board:
    def __init__(self, rows: int, cols: int,
                 initialTiles: List[List[Tile]] = None,
                 startR: int = 0,
                 startC: int = 0):

        self.rows = rows
        self.cols = cols
        self.startR = startR
        self.startC = startC
        self.bridgeMap = {}
        # Initialize grid with NORMAL tiles if no initialTiles provided
        if initialTiles is not None:
            self.tiles = initialTiles
        else:
            self.tiles = [[Tile.NORMAL for _ in range(cols)] for _ in range(rows)]

        self.initialTiles = [row[:] for row in self.tiles]

        # Bridge system
        self.bridgeGroups = {}
        self.bridgeState = {}
        self.initialBridgeState = {}

    def __repr__(self):
        return f"Board({self.rows}x{self.cols})"

    def reset(self):
        self.tiles = [row[:] for row in self.initialTiles]

        # Restore this board's recorded configuration, not a universal default.
        self.bridgeState = self.initialBridgeState.copy()

    def isInBounds(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols

    def getTile(self, r, c):
        if not self.isInBounds(r, c):
            return Tile.VOID

        try:
            return self.tiles[r][c]
        except IndexError:
            print("BOARD ERROR")
            print("rows:", self.rows)
            print("cols:", self.cols)
            print("actual rows:", len(self.tiles))
            print("actual cols:", len(self.tiles[r]))
            print("requested:", r, c)
            raise

    def setTile(self, r, c, tile):
        if self.isInBounds(r, c):
            self.tiles[r][c] = tile

    def setRow(self, rowIndex, tile):
        if 0 <= rowIndex < self.rows:
            self.tiles[rowIndex] = [tile] * self.cols

    def setColumn(self, colIndex, tile):
        if 0 <= colIndex < self.cols:
            for r in range(self.rows):
                self.tiles[r][colIndex] = tile

    # ============================
    # Bridge System
    # ============================

    def addBridge(self, switchPos, bridgeTiles):
        self.bridgeGroups[switchPos] = bridgeTiles
        self.bridgeState[switchPos] = True
        # The current loader supports only initially enabled bridge groups.
        self.initialBridgeState[switchPos] = self.bridgeState[switchPos]

    def toggleBridge(self, switchPos):

        if switchPos not in self.bridgeGroups:
            return

        self.bridgeState[switchPos] = not self.bridgeState[switchPos]

        newTile = (
            Tile.BRIDGE
            if self.bridgeState[switchPos]
            else Tile.VOID
        )

        for r, c in self.bridgeGroups[switchPos]:
            self.tiles[r][c] = newTile
