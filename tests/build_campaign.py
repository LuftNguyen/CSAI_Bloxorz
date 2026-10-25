"""Deterministic room/island layouts. Explicit --write replaces only ten levels."""
import argparse
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Layout:
    def __init__(self, number, rows, cols, start, goal):
        self.number = number
        self.grid = [['X'] * cols for _ in range(rows)]
        self.start, self.goal = start, goal
        self.bridges, self.switches, self.splits = [], [], []
        self.traps = []

    def room(self, top, left, bottom, right):
        for r in range(top, bottom + 1):
            for c in range(left, right + 1):
                self.grid[r][c] = '.'
        return self

    def put(self, positions, char):
        for r, c in positions:
            self.grid[r][c] = char
        return self

    def bridge(self, key, cells):
        self.put(cells, 'B')
        self.bridges.append(dict(id=key, initial_open=False, tiles=cells))
        return self

    def switch(self, position, kind, key, mode, fatal=False):
        self.put([position], kind)
        self.switches.append(dict(position=position, effects=[dict(bridge=key, mode=mode)]))
        if fatal:
            self.switches[-1]['fatal_close'] = True
        if mode == 'CLOSE':
            self.traps.append(dict(position=position, kind='fatal_close' if fatal else 'close_open_bridge', bridge=key))
        return self

    def trap_split(self, position, targets):
        self.split(position, targets)
        self.splits[-1]['fatal_split'] = True
        self.traps.append(dict(position=position, kind='fatal_split'))
        return self

    def split(self, position, targets):
        self.put([position], 'T')
        self.splits.append(dict(position=position, targets=targets))
        return self

    def data(self):
        self.put([self.start], 'S').put([self.goal], 'G')
        return dict(schema_version=2, level_id=self.number,
                    name=f'{self.number}: {NAMES[self.number]}', rows=len(self.grid),
                    cols=len(self.grid[0]), start=dict(r=self.start[0], c=self.start[1]),
                    grid=[''.join(row) for row in self.grid], bridges=self.bridges,
                    switches=self.switches, splits=self.splits,
                    design=dict(traps=self.traps))


NAMES = {1: 'Courtyard', 2: 'Crosswind galleries', 3: 'Fragile causeway',
         4: 'Two fragile turns', 5: 'Soft island crossing', 6: 'Heavy island crossing',
         7: 'Three islands', 8: 'Split across the fragile channel',
         9: 'Split and the island gate', 10: 'Twin gates expedition'}


def layouts():
    a = Layout(1, 9, 11, (1, 1), (7, 9)).room(1, 1, 7, 9)
    a.put([(r, 4) for r in range(1, 5)] + [(5, 7), (6, 7)], 'X')
    b = Layout(2, 15, 17, (1, 5), (9, 15))
    b.room(1, 5, 4, 11).room(5, 1, 9, 15).room(10, 5, 13, 11)
    b.put([(r, c) for r in range(6, 9) for c in range(7, 10)]
          + [(3, 9), (11, 7), (7, 3), (7, 13)], 'X')
    b.put([(5, 4), (9, 12), (12, 10)], 'X').put([(4, 7), (9, 11)], 'F')
    c = Layout(3, 10, 15, (1, 1), (7, 13)).room(1, 1, 5, 5).room(2, 8, 8, 13)
    c.put([(4, 6), (4, 7)], 'F').put([(2, 3), (6, 10)], 'X')
    c.put([(3, 2), (7, 9)], 'X').put([(2, 10), (3, 11)], 'F')
    d = Layout(4, 14, 14, (1, 1), (12, 12)).room(1, 1, 5, 5).room(1, 8, 5, 12).room(8, 8, 12, 12)
    d.put([(3, 6), (3, 7), (6, 10), (7, 10)], 'F').put([(2, 3), (9, 9)], 'X')
    d.put([(4, 1), (10, 9)], 'X').put([(2, 10), (9, 12)], 'F')
    e = Layout(5, 10, 16, (1, 1), (8, 14)).room(1, 1, 5, 5).room(3, 9, 8, 14)
    e.bridge('crossing', [(3, c) for c in range(6, 9)]).switch((5, 2), 'w', 'crossing', 'OPEN')
    e.put([(2, 3), (6, 12)], 'X')
    e.switch((2, 5), 'W', 'crossing', 'CLOSE', fatal=True).switch((5, 4), 'w', 'crossing', 'TOGGLE')
    e.switch((4, 1), 'W', 'crossing', 'OPEN').switch((4, 4), 'w', 'crossing', 'CLOSE')
    f = Layout(6, 11, 17, (6, 1), (2, 15)).room(1, 1, 7, 5).room(2, 9, 8, 15)
    f.bridge('crossing', [(5, c) for c in range(6, 9)]).switch((1, 5), 'W', 'crossing', 'TOGGLE')
    f.put([(3, 3), (4, 12), (5, 12)], 'X')
    f.switch((2, 1), 'W', 'crossing', 'OPEN').switch((7, 3), 'w', 'crossing', 'CLOSE')
    f.switch((4, 5), 'W', 'crossing', 'CLOSE', fatal=True).switch((6, 4), 'w', 'crossing', 'CLOSE')
    g = Layout(7, 11, 23, (1, 1), (1, 21)).room(1, 1, 5, 5).room(4, 9, 8, 13).room(1, 17, 6, 21)
    g.bridge('first', [(4, c) for c in range(6, 9)]).bridge('second', [(5, c) for c in range(14, 17)])
    g.switch((5, 2), 'w', 'first', 'OPEN').switch((8, 12), 'W', 'second', 'TOGGLE')
    g.put([(2, 3), (5, 11), (3, 19)], 'X')
    g.switch((1, 4), 'W', 'first', 'CLOSE').switch((6, 10), 'w', 'second', 'CLOSE')
    g.switch((4, 13), 'W', 'second', 'OPEN')
    g.switch((4, 2), 'w', 'first', 'OPEN').switch((7, 13), 'W', 'second', 'CLOSE', fatal=True)
    h = Layout(8, 10, 24, (1, 18), (8, 1)).room(1, 18, 4, 22).room(5, 1, 8, 4).room(5, 10, 8, 13)
    h.put([(6, c) for c in range(5, 10)], 'F').split((4, 21), [(7, 2), (7, 12)])
    h.put([(1, 1), (1, 4)], '.').trap_split((1, 22), [(1, 1), (1, 4)])
    h.bridge('landing', [(7, c) for c in range(1, 5)])
    h.switch((2, 19), 'w', 'landing', 'OPEN').switch((3, 20), 'w', 'landing', 'CLOSE', fatal=True)
    i = Layout(9, 17, 17, (14, 1), (1, 13))
    i.room(12, 1, 15, 5).room(8, 8, 11, 12).room(1, 11, 4, 14)
    i.bridge('gate', [(r, 12) for r in range(5, 8)])
    i.switch((10, 8), 'w', 'gate', 'OPEN').switch((8, 9), 'w', 'gate', 'CLOSE')
    i.switch((10, 12), 'w', 'gate', 'TOGGLE')
    i.switch((9, 8), 'w', 'gate', 'OPEN').switch((11, 12), 'w', 'gate', 'CLOSE', fatal=True)
    i.split((12, 4), [(3, 13), (11, 9)])
    i.put([(1, 1), (1, 4)], '.').trap_split((15, 5), [(1, 1), (1, 4)])
    j = Layout(10, 13, 26, (1, 20), (10, 1)).room(1, 20, 4, 24)
    j.room(7, 1, 10, 4).room(6, 8, 9, 11).room(7, 15, 10, 18)
    j.bridge('near', [(7, c) for c in range(12, 15)]).bridge('far', [(8, c) for c in range(5, 8)])
    j.switch((10, 17), 'w', 'near', 'OPEN').switch((9, 9), 'w', 'far', 'OPEN')
    j.put([(8, 3)], 'F').split((4, 23), [(8, 3), (7, 18)])
    j.switch((8, 16), 'w', 'near', 'CLOSE').switch((6, 10), 'w', 'far', 'CLOSE')
    j.switch((9, 2), 'w', 'near', 'OPEN')
    j.switch((7, 9), 'w', 'far', 'OPEN').switch((9, 18), 'w', 'near', 'CLOSE', fatal=True)
    j.put([(1, 1), (1, 4)], '.').trap_split((1, 24), [(1, 1), (1, 4)])
    return [a, b, c, d, e, f, g, h, i, j]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--preview', action='store_true', help='write docs/CAMPAIGN_MAPS.svg')
    args = parser.parse_args()
    for layout in layouts():
        data = layout.data()
        if args.write:
            (ROOT/f'levels/level{layout.number}.json').write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
        print(data['name'])
        print('\n'.join(data['grid']))
    if args.preview:
        palette = {'.': '#d9e2ec', 'S': '#8fbce6', 'G': '#55cc66',
                   'F': '#edac52', 'B': '#805c3b', 'w': '#3695dd',
                   'W': '#d95555', 'T': '#a679dd'}
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="980" height="1830" viewBox="0 0 980 1830">',
                 '<rect width="980" height="1830" fill="#142033"/>',
                 '<g font-family="sans-serif" fill="white">',
                 '<text x="20" y="28" font-size="20">Bloxorz: 10 island and courtyard layouts</text>',
                 '<text x="20" y="52" font-size="13">S start | G goal | F fragile | B closed bridge | w soft | W heavy | T split | ! fatal trap</text>']
        for index, layout in enumerate(layouts()):
            data = layout.data()
            fatal = {tuple(s['position']) for s in data['switches'] if s.get('fatal_close')}
            fatal.update(tuple(s['position']) for s in data['splits'] if s.get('fatal_split'))
            ox, oy = 20 + (index % 2) * 480, 90 + (index // 2) * 340
            parts.append(f'<text x="{ox}" y="{oy}" font-size="15">{escape(data["name"])}</text>')
            for r, row in enumerate(data['grid']):
                for c, tile in enumerate(row):
                    if tile == 'X':
                        continue
                    x, y = ox + c * 16, oy + 12 + r * 16
                    parts.append(f'<rect x="{x}" y="{y}" width="15" height="15" fill="{palette[tile]}"/>')
                    if tile != '.':
                        label = tile + ('!' if (r, c) in fatal else '')
                        parts.append(f'<text x="{x+2}" y="{y+12}" font-size="12" fill="white">{label}</text>')
            for split in data['splits']:
                for r, c in split['targets']:
                    parts.append(f'<circle cx="{ox+c*16+7}" cy="{oy+12+r*16+7}" r="5" fill="none" stroke="#ed74b8" stroke-width="2"/>')
        parts.append('</g></svg>')
        (ROOT/'docs/CAMPAIGN_MAPS.svg').write_text('\n'.join(parts)+'\n', encoding='utf-8')
