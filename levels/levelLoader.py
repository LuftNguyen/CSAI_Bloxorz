"""Validated legacy and schema_version=2 JSON levels; no GUI dependency."""
import json
from gameModel.board import Board, Tile
from gameModel.block import Block

CHAR_TILE_MAP = {'X': Tile.VOID, '.': Tile.NORMAL, 'F': Tile.FRAGILE,
                 'G': Tile.GOAL, 'S': Tile.NORMAL, 'w': Tile.SOFT_SWITCH,
                 'W': Tile.HEAVY_SWITCH, 'B': Tile.BRIDGE, 'T': Tile.SPLIT_SWITCH}


def loadLevelFromJson(filePath, isDebug=True):
    try:
        with open(filePath, encoding='utf-8') as stream:
            data = json.load(stream)
        return _load(data, isDebug)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        raise ValueError(f"Invalid level {filePath}: {exc}") from exc


def _load(data, debug=False):
    def require(condition, message):
        if not condition:
            raise ValueError(message)
    rows, cols = data['rows'], data['cols']
    require(type(rows) is int and type(cols) is int and rows > 0 and cols > 0, 'rows/cols must be positive integers')
    grid = data['grid']
    require(isinstance(grid, list) and len(grid) == rows and all(isinstance(row, str) and len(row) == cols for row in grid), 'grid dimensions do not match rows/cols')
    require(all(char in CHAR_TILE_MAP for row in grid for char in row), 'unknown grid character')
    require(sum(row.count('G') for row in grid) == 1, 'exactly one goal required')
    def position(value):
        require(isinstance(value, (list, tuple)) and len(value) == 2 and all(type(v) is int for v in value), 'coordinate must contain two integers')
        r, c = value
        require(0 <= r < rows and 0 <= c < cols, f'coordinate out of bounds: {value}')
        return r, c
    start = position([data['start']['r'], data['start']['c']])
    starts = [(r,c) for r,row in enumerate(grid) for c,v in enumerate(row) if v == 'S']
    require(not starts or starts == [start], 'S marker disagrees with start')
    require(grid[start[0]][start[1]] in '.S', 'start must be normal floor')
    board = Board(rows, cols, [[CHAR_TILE_MAP[v] for v in row] for row in grid], *start)
    version = data.get('schema_version', 1)
    require(type(version) is int and version in (1,2), 'unsupported schema_version')
    bridges = data.get('bridges', [])
    require(isinstance(bridges, list), 'bridges must be a list')
    occupied_bridge = set()
    if version == 1:
        require(not data.get('switches') and not data.get('splits') and not any('T' in row for row in grid),
                'advanced switches/splits require schema_version=2')
        canonical = {}
        seen_switch = set()
        for entry in bridges:
            switch = position(entry['switch'])
            require(switch not in seen_switch, 'duplicate legacy switch definition')
            seen_switch.add(switch)
            require(board.getTile(*switch) in (Tile.SOFT_SWITCH, Tile.HEAVY_SWITCH), 'legacy switch must reference w or W')
            tiles = tuple(sorted(position(p) for p in entry['tiles']))
            require(tiles and len(set(tiles)) == len(tiles), 'bridge tiles must be nonempty and unique')
            require(all(board.getTile(*p) == Tile.BRIDGE for p in tiles), 'legacy bridge tiles must reference B')
            if tiles not in canonical:
                require(not occupied_bridge.intersection(tiles), 'partially overlapping bridge groups')
                canonical[tiles] = switch
                board.addBridge(switch, list(tiles))
                occupied_bridge.update(tiles)
            else:
                board.switchEffects[switch] = ((canonical[tiles], 'TOGGLE'),)
    else:
        for entry in bridges:
            key = entry['id']
            require(isinstance(key, str) and key and key not in board.bridgeGroups, 'duplicate/invalid bridge id')
            opened = entry['initial_open']
            require(type(opened) is bool, 'initial_open must be boolean')
            tiles = [position(p) for p in entry['tiles']]
            require(tiles and len(set(tiles)) == len(tiles), 'bridge tiles must be nonempty and unique')
            require(not occupied_bridge.intersection(tiles), 'overlapping bridge groups')
            require(all(grid[r][c] in 'BX' for r,c in tiles), 'bridge cells must be B or X')
            occupied_bridge.update(tiles)
            board.addBridgeGroup(key, tiles, opened)
        entries = data.get('switches', [])
        require(isinstance(entries, list), 'switches must be a list')
        for entry in entries:
            switch = position(entry['position'])
            require(switch not in board.switchEffects, 'duplicate switch position')
            require(board.getTile(*switch) in (Tile.SOFT_SWITCH, Tile.HEAVY_SWITCH), 'switch must reference w or W')
            effects = []
            for effect in entry['effects']:
                key, mode = effect['bridge'], effect['mode']
                require(key in board.bridgeGroups, 'unknown bridge reference')
                require(mode in ('TOGGLE','OPEN','CLOSE'), 'unknown switch mode')
                require(key not in [e[0] for e in effects], 'duplicate bridge effect on one switch')
                effects.append((key,mode))
            require(effects, 'switch effects must not be empty')
            board.switchEffects[switch] = tuple(effects)
        splits = data.get('splits', [])
        require(isinstance(splits, list), 'splits must be a list')
        for entry in splits:
            switch = position(entry['position'])
            require(board.getTile(*switch) == Tile.SPLIT_SWITCH and switch not in board.splitTargets, 'invalid/duplicate split position')
            targets = tuple(position(p) for p in entry['targets'])
            require(len(targets) == 2 and targets[0] != targets[1], 'split requires two distinct destinations')
            board.splitTargets[switch] = targets
        split_cells = {(r,c) for r,row in enumerate(grid) for c,v in enumerate(row) if v == 'T'}
        require(split_cells == set(board.splitTargets), 'each T requires a split definition')
        switch_cells = {(r,c) for r,row in enumerate(grid) for c,v in enumerate(row) if v in 'wW'}
        require(switch_cells == set(board.switchEffects), 'each w/W requires effects in schema 2')
        bridge_cells = {(r,c) for r,row in enumerate(grid) for c,v in enumerate(row) if v == 'B'}
        require(bridge_cells <= occupied_bridge, 'each B requires a bridge definition in schema 2')
        for targets in board.splitTargets.values():
            require(all(board.getTile(*p) != Tile.VOID or p in occupied_bridge for p in targets),
                    'split destination is permanent void')
    board.initialTiles = [row[:] for row in board.tiles]
    if debug:
        print(f'Loaded {rows}x{cols} level; schema={version}, bridges={len(board.bridgeGroups)}')
    return board, Block(*start)
