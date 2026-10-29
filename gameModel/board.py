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
    SPLIT_SWITCH = 7

#costs for each tile type, used in uniform cost search
TILE_COST = {

    Tile.NORMAL: 1,

    Tile.GOAL: 1,

    Tile.SOFT_SWITCH: 0.5,

    Tile.HEAVY_SWITCH: 0.5,

    Tile.BRIDGE: 1,

    Tile.FRAGILE: 5,
    Tile.SPLIT_SWITCH: 0.5,
}

def _clone(value):
    """Structural copy of nested list/dict/set/tuple; other objects are shared."""
    kind = type(value)
    if kind is list:
        return [_clone(v) for v in value]
    if kind is dict:
        return {_clone(k): _clone(v) for k, v in value.items()}
    if kind is tuple:
        return tuple(_clone(v) for v in value)
    if kind is set:
        return {_clone(v) for v in value}
    return value

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
        self.switchEffects = {}
        self.splitTargets = {}
        self.fatalCloseSwitches = frozenset()
        self.fatalSplitSwitches = frozenset()
        self.fatalSwitch = None

    def __repr__(self):
        return f"Board({self.rows}x{self.cols})"

    def copy(self):
        new = Board.__new__(Board)
        for key, value in self.__dict__.items():
            new.__dict__[key] = _clone(value)
        return new
    
    def reset(self):
        self.tiles = [row[:] for row in self.initialTiles]

        # Restore this board's recorded configuration, not a universal default.
        self.bridgeState = self.initialBridgeState.copy()
        self.fatalSwitch = None

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
        # Legacy schema: groups are initially enabled.
        self.initialBridgeState[switchPos] = self.bridgeState[switchPos]
        self.switchEffects[switchPos] = ((switchPos, "TOGGLE"),)

    def addBridgeGroup(self, bridge_id, positions, opened):
        self.bridgeGroups[bridge_id] = [tuple(p) for p in positions]
        self.bridgeState[bridge_id] = opened
        self.initialBridgeState[bridge_id] = opened
        for r, c in positions:
            self.setTile(r, c, Tile.BRIDGE if opened else Tile.VOID)
        self.initialTiles = [row[:] for row in self.tiles]

    def applySwitch(self, position):
        if self.fatalSwitch is not None:
            return
        for bridge_id, mode in self.switchEffects.get(position, ()):
            if mode not in ("TOGGLE", "OPEN", "CLOSE"):
                raise ValueError(f"Unknown switch mode: {mode}")
            current = self.bridgeState[bridge_id]
            self.bridgeState[bridge_id] = not current if mode == "TOGGLE" else mode == "OPEN"
            tile = Tile.BRIDGE if self.bridgeState[bridge_id] else Tile.VOID
            for r, c in self.bridgeGroups[bridge_id]:
                self.setTile(r, c, tile)
        if position in self.fatalCloseSwitches:
            self.fatalSwitch = position

    def rules_key(self):
        return (frozenset((key, tuple(value)) for key, value in self.bridgeGroups.items()),
                frozenset((key, tuple(value)) for key, value in self.switchEffects.items()),
                frozenset((key, tuple(value)) for key, value in self.splitTargets.items()),
                self.fatalCloseSwitches, self.fatalSplitSwitches)

    def toggleBridge(self, switchPos):

        if self.fatalSwitch is not None:
            return

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
