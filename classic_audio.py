"""Presentation-only sound cues; searching the game model stays silent."""
from pathlib import Path
from gameModel.block import Direction, Orientation
from gameModel.board import Tile
from gameModel.rules import pressed


def sound_events(before, after, action, *, won=False, lost=False):
    if action == Direction.SWITCH:
        return ['select']
    landing = before.block.resultingState(action)
    tiles = [before.board.getTile(*p) for p in landing.occupied()]
    broken = any(t == Tile.FRAGILE and after.board.getTile(*p) == Tile.VOID
                 for p,t in zip(landing.occupied(),tiles))
    events = []
    if broken:
        events.append('break')
    elif Tile.FRAGILE in tiles:
        events.append('fragile')
    elif Tile.BRIDGE in tiles:
        events.append('bridge')
    elif any(t != Tile.VOID for t in tiles):
        events.append('stone')
    if pressed(after) - pressed(before):
        events.append('switch')
    if before.board.bridgeState != after.board.bridgeState:
        events.append('bridge')
    if before.block.orientation != Orientation.SPLIT and after.block.orientation == Orientation.SPLIT:
        events.append('split')
    elif before.block.orientation == Orientation.SPLIT and after.block.orientation != Orientation.SPLIT:
        events.append('merge')
    if won:
        events.append('win')
    elif lost:
        events.append('trap' if after.board.fatalSwitch is not None else 'fall')
    return list(dict.fromkeys(events))


class ClassicAudio:
    def __init__(self):
        from ursina import Audio
        folder = Path(__file__).resolve().parent/'assets/classic/audio'
        self.enabled = True
        self.clips = {p.stem: Audio(p, autoplay=False, volume=.65)
                      for p in sorted(folder.glob('*.wav'))}

    def play(self, events):
        if self.enabled:
            for name in events:
                clip = self.clips[name]
                clip.stop()
                clip.play()

    def stop(self):
        for clip in self.clips.values():
            clip.stop()

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled:
            self.stop()
        return self.enabled
