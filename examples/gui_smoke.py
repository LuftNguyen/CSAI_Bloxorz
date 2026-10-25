"""Instant-pose and real fall/replay checks; not manual desktop acceptance."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args()
    from panda3d.core import ClockObject, PNMImage, StringStream, loadPrcFileData
    loadPrcFileData('', 'audio-library-name null')
    from ursina import Ursina
    import view
    from gameModel.block import Block, Orientation
    from gameModel.gameController import GameController
    from gameModel.problem import Problem
    from gameModel.state import State
    from levels.levelLoader import loadLevelFromJson

    root = Path(__file__).resolve().parents[1]
    load = lambda n: loadLevelFromJson(root/f'levels/level{n}.json', False)
    board, block = load(1)
    with patch.object(view, 'Ursina', side_effect=lambda: Ursina(window_type='offscreen', development_mode=False)):
        ui = view.BloxorzView(GameController(board,block), Problem(State(board,block).copy()))
    clock = ClockObject.getGlobalClock()
    clock.setMode(ClockObject.MNonRealTime)
    clock.setDt(1/60)

    def tick(frames=1):
        for _ in range(frames):
            ui.app.taskMgr.step()
            ui.updateAnimations()  # Same post-sequence poll as Entity.update in run().

    def until(predicate, limit=600):
        for _ in range(limit):
            tick()
            if predicate():
                return
        raise AssertionError('Offscreen animation/transition failed to finish')

    def key(name):
        ui.handleUrsinaInput(name)
        if not ui.gameModel.hasWon and not ui.gameModel.isGameOver:
            assert not ui.isAnimating and ui._movement is None

    def capture(name):
        if args.capture_dir:
            args.capture_dir.mkdir(parents=True, exist_ok=True)
            tick(2)
            path = args.capture_dir/f'{name}.png'
            pixels = PNMImage()
            assert ui.app.win.getScreenshot(pixels), 'Offscreen screenshot readback failed'
            stream = StringStream()
            assert pixels.write(stream, 'capture.png'), 'Offscreen PNG encoding failed'
            path.write_bytes(stream.getData())
            assert path.stat().st_size > 0
            print('Capture:',path.resolve())

    try:
        ui.startMenu.start_game()
        with ExitStack() as stack:
            ordinary_animations = []
            for mesh in [ui.blockMesh] + ui.cubeMeshes:
                for method in ('animate_position', 'animate_scale'):
                    ordinary_animations.append(stack.enter_context(patch.object(mesh, method, wraps=getattr(mesh, method))))
            key('right arrow')
            assert tuple(ui.blockMesh.position) == (2.5,0,-1)
            key('right arrow')
            assert ui.gameModel.hasWon and tuple(ui.blockMesh.position) == (4,0,-1)
            ui.restartLevel()
            ui.handleUrsinaInput('left arrow')
            assert ui.gameModel.isGameOver and ui.isAnimating
            assert tuple(ui.blockMesh.position) == (-0.5,0,-1)
            until(lambda: not ui.isAnimating)
            assert not ui.gameModel.isGameOver

            ui.changeLevel(load(13))
            capture('bridge_before_move')
            old_tiles = tuple(ui.tileEntities)
            key('right arrow')
            assert ui.gameModel.board.bridgeState['crossing']
            assert tuple(ui.blockMesh.position) == (2.5,0,-1)
            assert tuple(ui.tileEntities) != old_tiles
            capture('bridge_after_move')

            # Heavy CLOSE through its verified witness at a low frame rate.
            clock.setDt(0.1)
            ui.restartLevel()
            data = json.loads((root/'levels/validation.json').read_text())
            witness = next(a for row in data['levels'] if row['level']==13
                           for a in row['activations'] if a['position']==[2,2])
            names = {'UP':'up arrow','DOWN':'down arrow','LEFT':'left arrow','RIGHT':'right arrow','SWITCH':'space'}
            for action in witness['actions']:
                key(names[action])
            assert not ui.gameModel.board.bridgeState['crossing']
            clock.setDt(1/60)

            ui.changeLevel(load(12))
            key('right arrow')
            key('right arrow')
            assert ui.gameModel.block.orientation == Orientation.SPLIT
            assert not ui.blockMesh.enabled and all(m.enabled for m in ui.cubeMeshes)
            assert [tuple(m.position) for m in ui.cubeMeshes] == [(1,0,-1),(6,0,-1)]
            key('space')
            assert ui.gameModel.block.active == 1
            key('space')
            for _ in range(4):
                key('right arrow')
            assert ui.gameModel.block.orientation == Orientation.LYING
            assert ui.blockMesh.enabled and not any(m.enabled for m in ui.cubeMeshes)
            key('right arrow')
            assert ui.gameModel.hasWon

            # Existing fragile tile, valid constructed pre-move pose; no data edit.
            from gameModel.board import Tile
            ui.changeLevel(load(6))
            ui.gameModel.block = Block(3,3,0,1,Orientation.LYING)
            ui.updateBlockMesh()
            ui.handleUrsinaInput('left arrow')
            assert ui.gameModel.board.getTile(3,2) == Tile.VOID
            assert tuple(ui.blockMesh.position) == (2,0,-3)
            assert ui.isAnimating
            until(lambda: not ui.isAnimating)
            assert ui.gameModel.board.getTile(3,2) == Tile.FRAGILE

            # Real A* still returns the same valid actions; replay snaps per frame.
            ui.changeLevel(load(1))
            ui.levelManager.currentLevel = 1
            with patch.object(ui.gameModel, 'executeMove', wraps=ui.gameModel.executeMove) as execute:
                ui.solve('astar')
                until(lambda: ui.levelManager.currentLevel == 2)
                assert execute.call_count == 2
            assert not ui.isAnimating and not ui.isSolving

            # Only fall remains asynchronous: cancel it before reset/change level.
            ui.changeLevel(load(1))
            ui.handleUrsinaInput('left arrow')
            ui.restartLevel()
            snapshot = State(ui.gameModel.board,ui.gameModel.block).copy()
            tick(120)
            assert State(ui.gameModel.board,ui.gameModel.block)==snapshot
            assert tuple(ui.blockMesh.position)==(1,0,-1)
            ui.handleUrsinaInput('left arrow')
            ui.changeLevel(load(12))
            snapshot = State(ui.gameModel.board,ui.gameModel.block).copy()
            tick(120)
            assert State(ui.gameModel.board,ui.gameModel.block)==snapshot
            assert tuple(ui.blockMesh.position)==(1,0,-1)

            # Reset also cancels a replay queued after an already-visible first step.
            from gameModel.block import Direction
            ui.changeLevel(load(1))
            ui.isSolving = True
            ui.autoSolution = [Direction.RIGHT, Direction.RIGHT]
            ui.autoIndex = 0
            ui.queueReplay()
            ui.updateAnimations()
            assert ui.autoIndex == 1 and ui._replayReady
            ui.restartLevel()
            tick(40)
            assert (ui.gameModel.block.r,ui.gameModel.block.c)==(1,1)
            assert not ui.isSolving and not ui._replayReady
            for method in ordinary_animations:
                method.assert_not_called()
        print('Offscreen instant movement OK: direct final poses, zero position/scale animators, bridge OPEN/CLOSE, fragile/fall/reset, split/SWITCH/merge, A* replay, cancellation')
    finally:
        ui.cancelReplay()
        ui.app.destroy()


if __name__ == '__main__':
    main()
