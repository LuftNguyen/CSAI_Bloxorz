"""Sound selection uses engine transitions, without initializing an audio device."""
from pathlib import Path
import unittest
import wave
from unittest.mock import Mock
from classic_audio import ClassicAudio, sound_events
from gameModel.block import Block, Direction as D, Orientation as O
from gameModel.board import Board, Tile as T
from gameModel.state import State
from gameModel.rules import transition


class ClassicAudioTests(unittest.TestCase):
    def state(self, tile=T.NORMAL):
        board = Board(3,8,[[T.NORMAL]*8 for _ in range(3)],1,0)
        board.setTile(1,2,tile)
        return State(board,Block(1,0,0,0,O.STANDING))

    def test_materials_and_source_unchanged(self):
        for tile, cue in ((T.NORMAL,'stone'),(T.FRAGILE,'fragile'),(T.BRIDGE,'bridge')):
            with self.subTest(tile=tile):
                before = self.state(tile)
                snapshot = before.copy()
                after, valid, _ = transition(before,D.RIGHT)
                self.assertTrue(valid)
                self.assertIn(cue,sound_events(before,after,D.RIGHT))
                self.assertEqual(before,snapshot)

    def test_fragile_break_and_fall(self):
        before = self.state(T.FRAGILE)
        before.block = Block(1,0,0,1,O.LYING)
        # A lying block at columns 0/1 stands at column 2.
        after, valid, loss = transition(before,D.RIGHT)
        self.assertFalse(valid)
        self.assertTrue(loss)
        self.assertEqual(sound_events(before,after,D.RIGHT,lost=True),['break','fall'])

    def test_switch_only_changes_selection_sound(self):
        before = self.state()
        before.block = Block.split(((1,0),(1,6)))
        after, valid, _ = transition(before,D.SWITCH)
        self.assertTrue(valid)
        self.assertEqual(sound_events(before,after,D.SWITCH),['select'])

    def test_goal_and_trap_cues(self):
        before = self.state()
        after, _, _ = transition(before,D.RIGHT)
        self.assertIn('win',sound_events(before,after,D.RIGHT,won=True))
        after.board.fatalSwitch = (1,2)
        self.assertIn('trap',sound_events(before,after,D.RIGHT,lost=True))

    def test_mute_stops_sounds_and_blocks_new_playback(self):
        audio = ClassicAudio.__new__(ClassicAudio)
        audio.enabled = True
        audio.clips = {'stone':Mock()}
        audio.play(['stone'])
        audio.clips['stone'].play.assert_called_once()
        self.assertFalse(audio.toggle())
        audio.play(['stone'])
        audio.clips['stone'].play.assert_called_once()
        self.assertEqual(audio.clips['stone'].stop.call_count,2)

    def test_all_assets_are_non_silent_pcm(self):
        folder = Path(__file__).resolve().parents[1]/'assets/classic/audio'
        files = list(folder.glob('*.wav'))
        self.assertEqual(len(files),11)
        for path in files:
            with self.subTest(sound=path.stem), wave.open(str(path),'rb') as clip:
                self.assertEqual((clip.getnchannels(),clip.getsampwidth(),clip.getframerate()),(1,2,22050))
                self.assertGreater(clip.getnframes(),1000)
                self.assertNotEqual(set(clip.readframes(clip.getnframes())),{0})
