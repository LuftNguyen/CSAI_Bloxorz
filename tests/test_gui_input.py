"""GUI input wiring regression; uses mocks without opening a window."""
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from gameModel.block import Block
from gameModel.board import Board
from gameModel.gameController import GameController
from inputHandler import InputHandler


@unittest.skipUnless(importlib.util.find_spec('ursina'), 'GUI dependencies not installed')
class GuiInputTests(unittest.TestCase):
    def test_dispatcher_preserved_and_entity_receives_press_once(self):
        from view import BloxorzView

        view = BloxorzView.__new__(BloxorzView)
        original_dispatcher = Mock()
        view.app = SimpleNamespace(input=original_dispatcher, run=Mock())
        view.gameModel = GameController(Board(7, 7), Block(3, 3))
        view.inputHandler = InputHandler()
        view.gameStarted = True
        view.isPaused = view.isAnimating = view.isSolving = False
        view.destroyTileEntities = Mock()
        view.renderBoard = Mock()
        view.updateBlockMesh = Mock()
        view.togglePause = Mock()
        view.restartLevel = Mock()
        with patch('view.Entity') as entity:
            view.run()
            self.assertIs(view.app.input, original_dispatcher)
            callback = entity.call_args.kwargs['input']
            callback('right arrow')
            self.assertEqual((view.gameModel.block.r, view.gameModel.block.c), (3, 4))
            after_press = view.gameModel.block.copy()
            callback('right arrow up')
            self.assertEqual(view.gameModel.block, after_press)
            view.updateBlockMesh.assert_called_once()
            callback('p')
            callback('p up')
            view.togglePause.assert_called_once()
            callback('r')
            callback('r up')
            view.restartLevel.assert_called_once()
        view.app.run.assert_called_once()
