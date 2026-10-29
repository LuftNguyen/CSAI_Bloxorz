"""Real offscreen classic rendering, menu/input checks and optional PNG captures."""
import argparse
from pathlib import Path
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture-dir', type=Path)
    args = parser.parse_args()
    from panda3d.core import ClockObject, PNMImage, StringStream, loadPrcFileData
    loadPrcFileData('', 'audio-library-name null')
    from ursina import Ursina, camera, window, scene
    import view
    from gameModel.gameController import GameController
    from gameModel.problem import Problem
    from gameModel.state import State
    from levels.levelLoader import loadLevelFromJson

    root = Path(__file__).resolve().parents[1]
    load = lambda n: loadLevelFromJson(root/f'tests/fixtures/legacy/level{n}.json', False)
    b,k = load(1)
    initial = State(b,k).copy()
    with patch.object(view, 'Ursina', side_effect=lambda: Ursina(window_type='offscreen',
                       size=(1280,800), development_mode=False)):
        ui = view.BloxorzView(GameController(b,k),Problem(initial.copy()))
    camera.ui_lens.set_film_size(camera._ui_size*.5*window.aspect_ratio,camera._ui_size*.5)
    clock = ClockObject.getGlobalClock()
    clock.setMode(ClockObject.MNonRealTime)
    clock.setDt(1/60)

    def tick(n=1):
        for _ in range(n):
            ui.app.taskMgr.step()
            ui.updateAnimations()

    def capture(name):
        tick(3)
        image = PNMImage()
        assert ui.app.win.getScreenshot(image)
        assert .01 < image.getAverageGray() < .95, 'Blank or overexposed rendering'
        print(name, "mean gray", image.getAverageGray(), flush=True)
        if args.capture_dir:
            args.capture_dir.mkdir(parents=True,exist_ok=True)
            stream = StringStream()
            assert image.write(stream,'capture.png')
            target = args.capture_dir/f'{name}.png'
            target.write_bytes(stream.getData())
            print('Capture:',target,flush=True)

    def choose(number, campaign=False):
        ui.cancelReplay()
        b,k = (loadLevelFromJson(root/f'levels/level{number}.json',False) if campaign else load(number))
        ui.gameModel = GameController(b,k)
        ui.problem = Problem(State(b,k).copy())
        ui.levelManager.currentLevel = number
        ui.moveCount = 0
        ui.isAnimating = ui.isPaused = False
        ui.destroyTileEntities()
        ui.setupCamera()
        ui.renderBoard()
        ui.updateBlockMesh()

    finish_step = ui.finishStep
    def check_surface_continuity(direction=None):
        visible = [(mesh, [part.get_mat(scene) for part in mesh._visual_parts])
                   for mesh in [ui.blockMesh, *ui.cubeMeshes] if mesh.enabled]
        finish_step(direction)
        for mesh, matrices in visible:
            if mesh.enabled:  # Split/merge deliberately replaces the visible meshes.
                assert all(part.get_mat(scene).almost_equal(matrix, 1e-4)
                           for part, matrix in zip(mesh._visual_parts, matrices)), 'Faces jumped at landing'
    ui.finishStep = check_surface_continuity

    try:
        capture('01_start_menu')
        ui.startMenu.start_game()
        capture('02_stage_01')
        assert len([e for e in ui.tileEntities if e.name=='goal_hole']) == 1
        ui.solverButton.on_click()
        assert ui.solverMenu.enabled and ui.isPaused and not ui.pauseMenu.enabled
        ui.handleUrsinaInput('right arrow')
        assert State(ui.gameModel.board,ui.gameModel.block) == initial
        capture('02b_solver_from_hud')
        ui.solverMenu.cancel_button.on_click()
        assert not ui.isPaused and not ui.solverMenu.enabled and not ui.pauseMenu.enabled
        ui.solverButton.on_click()
        ui.handleUrsinaInput('p')
        assert not ui.isPaused and not ui.solverMenu.enabled and not ui.pauseMenu.enabled
        # Each real menu button must route to its matching solver.
        with patch.object(ui, 'solve') as solve:
            for label, algorithm in (('BFS','bfs'), ('DFS','dfs'), ('UCS','ucs'), ('A*','astar')):
                ui.solverButton.on_click()
                next(e for e in ui.solverMenu.elements if getattr(e, 'text', None) == label).on_click()
                solve.assert_called_with(algorithm)
                assert not ui.isPaused and not ui.solverMenu.enabled
        ui.handleUrsinaInput('right arrow')
        while ui._roll is not None:
            tick()
        assert ui.moveCount == 1 and ui.gameModel.block.c == 2
        capture('03_block_lying')
        ui.restartLevel()
        assert ui.moveCount == 0
        assert State(ui.gameModel.board,ui.gameModel.block) == initial
        ui.togglePause()
        capture('04_pause_menu')
        assert ui.pauseMenu.enabled
        ui.toggleSound()
        assert not ui.sound.enabled and ui.soundButton.text == 'SOUND: OFF'
        ui.toggleSound()
        assert ui.sound.enabled and ui.soundButton.text == 'SOUND: ON'
        ui.pauseMenu.solver()
        assert ui.solverMenu.enabled
        capture('05_solver_menu')
        ui.solverMenu.cancel_button.on_click()
        choose(1)
        ui.solverButton.on_click()
        next(e for e in ui.solverMenu.elements if getattr(e, 'text', None) == 'A*').on_click()
        ui.solverButton.on_click()  # A running replay cannot open another solver.
        assert not ui.solverMenu.enabled and not ui.isPaused and ui.isSolving
        for _ in range(600):
            tick()
            if ui.levelManager.currentLevel == 2:
                break
        assert ui.levelManager.currentLevel == 2
        assert ui.moveCount == 0 and ui.stageText.text == 'STAGE 02'
        for number in (5,8):
            choose(number, campaign=True)
            capture(f'06_stage_{number:02d}')
        choose(13)
        capture('07_bridge_closed')
        ui.handleUrsinaInput('right arrow')
        while ui._roll is not None:
            tick()
        assert ui.gameModel.board.bridgeState['crossing']
        capture('08_bridge_open')
        ui.handleUrsinaInput('down arrow')
        tick(6)
        assert ui._roll is not None
        capture('09_surface_mid_roll')
        while ui._roll is not None:
            tick()
        capture('10_surface_landed')
        ui.handleUrsinaInput('up arrow')
        while ui._roll is not None:
            tick()
        assert ui.theme.textures['oxidized_metal'].filtering == 'mipmap'
        print('Textured faces and rims remain continuous across successive landings; metal mipmapping enabled')
        print('Classic graphics smoke passed: HUD solver, cancel/P, all solver buttons, bridge views, input, reset and A* replay')
    finally:
        ui.cancelReplay()
        ui.app.destroy()


if __name__ == '__main__':
    main()
