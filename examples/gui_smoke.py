"""Edge rolling and real fall/replay checks; not manual desktop acceptance."""
import argparse
from contextlib import ExitStack
import json
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args()
    from panda3d.core import ClockObject, PNMImage, StringStream, loadPrcFileData, Point2
    loadPrcFileData('', 'audio-library-name null')
    from ursina import Ursina
    import view
    from gameModel.block import Block, Orientation
    from gameModel.gameController import GameController
    from gameModel.problem import Problem
    from gameModel.state import State
    from levels.levelLoader import loadLevelFromJson

    root = Path(__file__).resolve().parents[1]
    load = lambda n: loadLevelFromJson(root/f'tests/fixtures/legacy/level{n}.json', False)
    board, block = load(1)
    with patch.object(view, 'Ursina', side_effect=lambda: Ursina(window_type='offscreen', development_mode=False)):
        ui = view.BloxorzView(GameController(board,block), Problem(State(board,block).copy()))
    # Offscreen windows do not emit the onscreen resize event that sizes the
    # UI lens. Match Window.update_aspect_ratio so captures include real HUDs.
    from ursina import camera, window
    camera.ui_lens.set_film_size(camera._ui_size * .5 * window.aspect_ratio,
                                 camera._ui_size * .5)
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
        if ui._roll is not None:
            until(lambda: ui._roll is None)
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

    def assert_bridge_visible(visible):
        # Legacy stage 13: both the slab and its soft shadow disappear on CLOSE.
        for x, z in ((4, -2), (4.16, -2.12)):
            entities = [e for e in ui.tileEntities if abs(e.x-x) < 1e-4 and abs(e.z-z) < 1e-4]
            assert len(entities) == int(visible), (visible, x, z, entities)

    try:
        ui.startMenu.start_game()
        native_aspect = camera.lens.get_aspect_ratio()
        for aspect in (16/9, 4/3, 9/16, 21/9):
            camera.lens.set_aspect_ratio(aspect)
            for number in range(1,11):
                ui.changeLevel(loadLevelFromJson(root/f'levels/level{number}.json', False))
                for point in ui._cameraBounds:
                    projected = Point2()
                    assert camera.lens.project(camera._cam.get_relative_point(view.scene, point), projected)
                    assert abs(projected.x) <= 0.82 and abs(projected.y) <= 0.76, (number, aspect)
        camera.lens.set_aspect_ratio(9/16)
        ui.updateAnimations(0)
        assert abs(ui._cameraAspect-9/16) < 1e-4
        camera.lens.set_aspect_ratio(native_aspect)
        ui.changeLevel(load(1))
        print('Camera bounds: 10 stages at 4 aspect ratios plus resize refit passed')
        with ExitStack() as stack:
            ordinary_animations = []
            for mesh in [ui.blockMesh] + ui.cubeMeshes:
                for method in ('animate_position', 'animate_scale'):
                    ordinary_animations.append(stack.enter_context(patch.object(mesh, method, wraps=getattr(mesh, method))))
            ui.handleUrsinaInput('right arrow')
            assert ui._roll is not None and ui.isAnimating
            tick(6)
            assert 0 < ui.blockMesh.rotation_z < 90
            capture('standing_mid_roll')
            until(lambda: ui._roll is None)
            assert tuple(ui.blockMesh.position) == (2.5,0,-1)
            # The lying block must tip around its long edge, not slide sideways.
            ui.handleUrsinaInput('down arrow')
            tick(6)
            assert -90 < ui.blockMesh.rotation_x < 0
            assert ui.blockMesh.y > 0
            capture('horizontal_mid_roll')
            until(lambda: ui._roll is None)
            key('up arrow')
            key('right arrow')
            assert ui.gameModel.hasWon and tuple(ui.blockMesh.position) == (4,0,-1)
            ui.restartLevel()
            key('left arrow')
            assert ui.gameModel.isGameOver and ui.isAnimating
            assert tuple(ui.blockMesh.position) == (-0.5,0,-1)
            until(lambda: not ui.isAnimating)
            assert not ui.gameModel.isGameOver

            ui.changeLevel(load(13))
            assert_bridge_visible(False)
            capture('bridge_before_move')
            old_tiles = tuple(ui.tileEntities)
            key('right arrow')
            assert ui.gameModel.board.bridgeState['crossing']
            assert_bridge_visible(True)
            assert tuple(ui.blockMesh.position) == (2.5,0,-1)
            assert tuple(ui.tileEntities) != old_tiles
            capture('bridge_after_move')

            # Heavy CLOSE through its verified witness at a low frame rate.
            clock.setDt(0.1)
            ui.restartLevel()
            data = json.loads((root/'tests/fixtures/legacy/validation.json').read_text())
            witness = next(a for row in data['levels'] if row['level']==13
                           for a in row['activations'] if a['position']==[2,2])
            names = {'UP':'up arrow','DOWN':'down arrow','LEFT':'left arrow','RIGHT':'right arrow','SWITCH':'space'}
            for action in witness['actions']:
                key(names[action])
            assert not ui.gameModel.board.bridgeState['crossing']
            assert_bridge_visible(False)
            capture('bridge_after_close')
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
            key('left arrow')
            assert ui.gameModel.board.getTile(3,2) == Tile.VOID
            assert tuple(ui.blockMesh.position) == (2,0,-3)
            assert ui.isAnimating
            until(lambda: not ui.isAnimating)
            assert ui.gameModel.board.getTile(3,2) == Tile.FRAGILE

            # Real A* returns the same actions; replay waits for each landing.
            ui.changeLevel(load(1))
            ui.levelManager.currentLevel = 1
            with patch.object(ui.gameModel, 'executeMove', wraps=ui.gameModel.executeMove) as execute:
                ui.solve('astar')
                until(lambda: ui.levelManager.currentLevel == 2)
                assert execute.call_count == 2
            assert not ui.isAnimating and not ui.isSolving

            # Cancel a fall after landing, before reset/change level.
            ui.changeLevel(load(1))
            key('left arrow')
            ui.restartLevel()
            snapshot = State(ui.gameModel.board,ui.gameModel.block).copy()
            tick(120)
            assert State(ui.gameModel.board,ui.gameModel.block)==snapshot
            assert tuple(ui.blockMesh.position)==(1,0,-1)
            key('left arrow')
            ui.changeLevel(load(12))
            snapshot = State(ui.gameModel.board,ui.gameModel.block).copy()
            tick(120)
            assert State(ui.gameModel.board,ui.gameModel.block)==snapshot
            assert tuple(ui.blockMesh.position)==(1,0,-1)

            # Reset also cancels a replay queued after its first landing.
            from gameModel.block import Direction
            ui.changeLevel(load(1))
            ui.isSolving = True
            ui.autoSolution = [Direction.RIGHT, Direction.RIGHT]
            ui.autoIndex = 0
            ui.queueReplay()
            ui.updateAnimations()
            assert ui._roll is not None
            until(lambda: ui._roll is None)
            assert ui.autoIndex == 1 and ui._replayReady
            ui.restartLevel()
            tick(40)
            assert (ui.gameModel.block.r,ui.gameModel.block.c)==(1,1)
            assert not ui.isSolving and not ui._replayReady
            # Cancel halfway through a real roll, with no delayed landing effects.
            ui.changeLevel(load(13))
            ui.handleUrsinaInput('right arrow')
            tick(6)
            assert ui._roll is not None
            ui.restartLevel()
            snapshot = State(ui.gameModel.board,ui.gameModel.block).copy()
            tick(30)
            assert State(ui.gameModel.board,ui.gameModel.block) == snapshot
            assert tuple(ui.blockMesh.rotation) == (0,0,0)
            assert ui._roll is None and not ui.isAnimating
            assert_bridge_visible(False)
            for method in ordinary_animations:
                method.assert_not_called()
            # Play every campaign stage through real rolls at a second frame rate.
            clock.setDt(.1)
            manifest = json.loads((root/'levels/validation.json').read_text())
            for record in manifest['levels']:
                ui.changeLevel(loadLevelFromJson(root/f'levels/level{record["level"]}.json', False))
                if record['level'] in (7, 10):
                    capture(f'campaign_{record["level"]}_initial')
                for action in record['solution']['actions']:
                    key(names[action])
                assert ui.gameModel.hasWon, record['level']
                assert not ui.gameModel.isGameOver
            for method in ordinary_animations:
                method.assert_not_called()
            clock.setDt(1/60)
            print('All 10 current campaign stages: real GUI input replay passed')
            # Complete a manual win, including visible fall and solid black frame.
            record = next(r for r in manifest['levels'] if r['level'] == 7)
            ui.levelManager.currentLevel = 7
            ui.changeLevel(loadLevelFromJson(root/'levels/level7.json', False))
            for action in record['solution']['actions']:
                key(names[action])
            assert ui._winPhase == 'fall' and ui.isAnimating
            assert all(tile.enabled for tile in ui.tileEntities)
            tick(24)
            assert ui._winPhase == 'fall' and -3.5 < ui.blockMesh.y < -0.1
            capture('goal_fall')
            until(lambda: ui._winPhase == 'collapse')
            poses = [(tile, tile.y, tuple(tile.scale)) for tile in ui.tileEntities]
            tick(18)
            assert any(tile.y < y-0.03 for tile, y, _ in poses)
            assert any(abs(tile.y-y) < 1e-6 for tile, y, _ in poses), 'Wave must be staggered'
            assert any(tile.scale_x < scale[0]*0.9 for tile, _, scale in poses)
            capture('board_disappearing_wave')
            until(lambda: ui._winPhase == 'blackout')
            assert not ui.blockMesh.enabled and ui.winBlackout.enabled
            capture('goal_blackout')
            black_pixels = PNMImage()
            assert ui.app.win.getScreenshot(black_pixels)
            assert black_pixels.getAverageGray() < 0.001, 'Blackout must cover HUD and board'
            tick(30)
            assert ui.levelManager.currentLevel == 7
            until(lambda: ui.levelManager.currentLevel == 8)
            assert not ui.winBlackout.enabled and not ui.isAnimating
            capture('after_goal_next_level')
            print('Manual goal fall, staggered falling/shrinking tiles, full black second and next level passed')
            # Cancel real delayed tile sequences in the middle of the wave.
            ui.levelManager.currentLevel = 7
            ui.changeLevel(loadLevelFromJson(root/'levels/level7.json', False))
            for action in record['solution']['actions']:
                key(names[action])
            until(lambda: ui._winPhase == 'collapse')
            tick(18)
            ui.restartLevel()
            restarted = State(ui.gameModel.board, ui.gameModel.block).copy()
            restored_tiles = [(tile, tuple(tile.position), tuple(tile.scale)) for tile in ui.tileEntities]
            tick(180)
            assert ui.levelManager.currentLevel == 7
            assert State(ui.gameModel.board, ui.gameModel.block) == restarted
            assert all(tile.enabled and tuple(tile.position) == pos and tuple(tile.scale) == scale
                       for tile, pos, scale in restored_tiles)
            assert not ui.winBlackout.enabled and ui._winPhase is None
            print('Restart during real tile wave cancels delayed transforms and level advance')
            # Fatal CLOSE: use a generated witness through real input/frame clock.
            fatal_data = json.loads((root/'levels/level5.json').read_text())
            fatal_position = next(s['position'] for s in fatal_data['switches'] if s.get('fatal_close'))
            witness = next(a for row in manifest['levels'] if row['level'] == 5
                           for a in row['activations'] if a['position'] == fatal_position)
            ui.changeLevel(loadLevelFromJson(root/'levels/level5.json', False))
            initial = State(ui.gameModel.board, ui.gameModel.block).copy()
            for action in witness['actions']:
                key(names[action])
            assert ui.gameModel.isGameOver and ui.isAnimating
            assert ui.gameModel.board.fatalSwitch == tuple(fatal_position)
            assert ui._fatalRemaining == 5.0 and ui.fatalMessage.enabled
            key('right arrow')
            assert ui._fatalRemaining == 5.0
            capture('fatal_close_countdown')
            tick(240)  # Still before 5 seconds, including capture frames.
            assert ui.gameModel.isGameOver and ui._fatalRemaining > 0
            until(lambda: ui._fatalRemaining is None)
            assert 'YOU LOSE' in ui.fatalMessage.text and ui.gameModel.isGameOver
            capture('fatal_close_loss')
            until(lambda: not ui.gameModel.isGameOver)
            assert State(ui.gameModel.board, ui.gameModel.block) == initial
            assert not ui.fatalMessage.enabled and not ui.isAnimating
            # A manual reset cancels the countdown completely.
            for action in witness['actions']:
                key(names[action])
            ui.restartLevel()
            tick(420)
            assert State(ui.gameModel.board, ui.gameModel.block) == initial
            assert not ui.fatalMessage.enabled and ui._fatalRemaining is None
            print('Fatal CLOSE: 5-second countdown, loss notice, reset and cancellation passed')
            split_data = json.loads((root/'levels/level8.json').read_text())
            split_position = next(s['position'] for s in split_data['splits'] if s.get('fatal_split'))
            witness = next(a for row in manifest['levels'] if row['level'] == 8
                           for a in row['activations'] if a['position'] == split_position)
            ui.changeLevel(loadLevelFromJson(root/'levels/level8.json', False))
            initial = State(ui.gameModel.board, ui.gameModel.block).copy()
            for action in witness['actions']:
                key(names[action])
            assert ui.gameModel.isGameOver and ui.gameModel.block.orientation == Orientation.SPLIT
            assert all(m.enabled for m in ui.cubeMeshes) and not ui.blockMesh.enabled
            assert 'Split trap!' in ui.fatalMessage.text and ui._fatalRemaining == 5
            capture('split_trap_countdown')
            until(lambda: ui._fatalRemaining is None)
            assert 'YOU LOSE' in ui.fatalMessage.text
            until(lambda: not ui.gameModel.isGameOver)
            assert State(ui.gameModel.board, ui.gameModel.block) == initial
            assert not ui.fatalMessage.enabled
            print('Split trap: teleported cubes, 5-second countdown, loss and reset passed')
        print('Offscreen rolling OK: rigid edge turns, landing effects, bridge OPEN/CLOSE, fragile/fall/reset, split/SWITCH/merge, A* replay, cancellation')
    finally:
        ui.cancelReplay()
        ui.app.destroy()


if __name__ == '__main__':
    main()
