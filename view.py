from ursina import *
from math import ceil
from panda3d.core import Point2
from animation_sync import AnimationCompletion

from gameModel.gameController import GameController
from gameModel.block import  Orientation, Direction
from gameModel.board import Tile
from inputHandler import InputHandler, Utility
from menu import *
from levels.levelManager import LevelManager

from runner import run_search, validate_solution
from search.contracts import SearchLimits
from gameModel.problem import Problem
from gameModel.state import State

class BloxorzView:
    def __init__(self, gameModel: GameController, problem):
        self.app = Ursina()
        self.gameModel = gameModel
        self.inputHandler = InputHandler()
        self.isPaused = False
        self.gameStarted = False
        self.isAnimating = False
        self.isSolving = False
        self._pendingCalls = []
        self._movement = None
        self._animationGeneration = 0
        self._presentingMove = False
        self._replayReady = False
        self.replayInterval = 0.5  # Pause between replay actions; manual moves stay instant.
        self._replayRemaining = 0.0
        self._fatalRemaining = None
        self._fatalNotice = False
        self._winPhase = None
        self._blackoutRemaining = None
        self._winTilePoses = []

        self.problem = problem
        self.solution = []
        self.autoindex = 0
        self.levelManager = LevelManager()
        self.algorithmList = ["BFS", "DFS", "UCS", "A*"]

        # Visuals & Setup
        window.color = color.black50
        self.setupLighting()
        self.setupCamera()

        # Instantiate Menus
        self.startMenu = StartMenu(on_start_callback=self.startGame)
        self.pauseMenu = PauseMenu(
            on_resume_callback=self.resumeGame,
            on_restart_callback=self.restartLevel,
            on_next_level_callback=self.loadNextLevel,
            on_solver_callback= self.showSolverMenu
        )
        self.solverMenu = SolverMenu(self.algorithmList, self.handleAlgorithmSelected)
        self.solverMessage = Text(text="A*: ready (h=0); BFS/DFS/UCS: not implemented", x=-0.85, y=0.46, scale=0.8)
        self.fatalMessage = Text(text='', origin=(0,0), y=0.25, scale=1.5,
                                 color=color.red, enabled=False)
        self.winBlackout = Entity(parent=camera.ui, model='quad', color=color.black,
                                  scale=99, z=-100, collider='box', enabled=False)

    def startGame(self):
        self.gameStarted = True
        self.tileColors = {
            Tile.NORMAL:       color.light_gray,
            Tile.GOAL:         color.lime,
            Tile.FRAGILE:      color.orange,
            Tile.SOFT_SWITCH:  color.cyan,
            Tile.HEAVY_SWITCH: color.red,
            Tile.BRIDGE:       color.brown,
            Tile.SPLIT_SWITCH: color.violet
        }

        self.tileEntities = []
        self.effectTileEntities = []
        self.renderBoard()

        # 3D Block mesh creation
        self.blockMesh = Entity(
            model='cube',
            color=color.azure,
            texture='white_cube',   # Sharpens edges
            origin_y=-0.5  # Pivot at the bottom face of the block
        )
        self.cubeMeshes = [Entity(model='cube', texture='white_cube', origin_y=-0.5) for _ in range(2)]
        self.controlsText = Text(text="WASD / arrows: roll | Space: switch cube | P: pause | R: restart",
                                 x=-0.85, y=-0.46, scale=0.8)
        self.newGameButton = Button(text="New Game", scale=(0.15, 0.04), position=(0.72, 0.46), on_click=self.newGame)
        self.restartButton = Button(text="Restart", scale=(0.15, 0.04), position=(0.72, 0.40), on_click=self.restartLevel)
        self.updateBlockMesh()

    def newGame(self):
        self.levelManager.currentLevel = 1
        self.changeLevel(self.levelManager.loadLevel())

    def showSolverMenu(self):
        if not self.gameStarted or not self.isPaused:
            return

        self.solverMenu.show()
        self.isPaused = True

    def handleAlgorithmSelected(self, algo_name: str):
        self.isPaused = False
        self.isSolving = True
        """Centralized handler for running solvers."""
        print(f"Algorithm selected: {algo_name}")

        match algo_name:

            case "BFS":
                self.solveBFS()

            case "DFS":
                self.solveDFS()

            case "UCS":
                self.solveUCS()

            case "A*":
                self.solveAStar()
        
    
    def solveDFS(self):
        print("Solving using DFS.........")
        self.solve("dfs")

    def solveUCS(self):
        print("Solving using UCS.........")
        self.solve("ucs")
    
    def solveBFS(self):
        print("Solving using BFS........")
        self.solve("bfs")

    def solveAStar(self):
        print("Solving using A*..........")
        self.solve("astar")
        
    def resumeGame(self):
        self.isPaused = False

    def unlockControlAll(self):
        """
        Set all attributes that could lock control for block movement to false
        """
        self.isPaused = False
        self.isAnimating = False
        self.isSolving = False

    def destroyTileEntities(self):
        """Destroys existing tile entities to prevent stacking duplicate meshes."""
        if hasattr(self, 'tileEntities') and self.tileEntities:
            for entity in self.tileEntities:
                destroy(entity)
        self.tileEntities = []
        self.effectTileEntities = []

    def restartLevel(self):
        """Resets the game model and refreshes 3D visual representations."""
        if not self.gameStarted:
            return
        print("Restarting level...")

        self.cancelReplay()
        self.pauseMenu.disable()
        self.solverMenu.hide()

        # 1. Block inputs during reset state transition
        self.isAnimating = True
        
        # 2. Reset underlying logical model (board layout, block coords, flags)
        self.gameModel.reset()

        # 3. Clean up old 3D board meshes and re-render fresh tiles
        self.destroyTileEntities()
        self.renderBoard()

        # 4. Reset block mesh rotation and snap position directly to starting tile
        self.blockMesh.rotation = (0, 0, 0)
        self.updateBlockMesh()

        # 5. Unlock controls for gameplay
        self.unlockControlAll()
        self.problem = Problem(
            State(
                self.gameModel.board,
                self.gameModel.block
            )
        )

    def togglePause(self):
        if not self.gameStarted or self.isSolving or self.isAnimating:
            return
        self.isPaused = not self.isPaused
        self.pauseMenu.toggle()

    def setupCamera(self):
        board = self.gameModel.board
        cells = {(r, c) for r, row in enumerate(board.initialTiles)
                 for c, tile in enumerate(row) if tile != Tile.VOID}
        cells.update(p for group in board.bridgeGroups.values() for p in group)
        if not cells:
            cells = {(board.startR, board.startC)}
        left, right = min(c for _, c in cells)-0.55, max(c for _, c in cells)+0.55
        back, front = -max(r for r, _ in cells)-0.55, -min(r for r, _ in cells)+0.55
        target = Vec3((left+right)/2, 0.75, (back+front)/2)
        self._cameraBounds = [Vec3(x, y, z) for x in (left, right)
                              for y in (-0.6, 2.1) for z in (back, front)]
        distance = max(right-left, front-back, 3)
        # Fit the actual lens, including standing-block height and HUD margins.
        # This also handles tall/narrow windows instead of assuming 16:9.
        for _ in range(80):
            camera.position = target + Vec3(0, distance, -distance)
            camera.look_at(target)
            fits = True
            for point in self._cameraBounds:
                projected = Point2()
                local = camera._cam.get_relative_point(scene, point)
                if not camera.lens.project(local, projected) or abs(projected.x) > 0.82 or abs(projected.y) > 0.76:
                    fits = False
                    break
            if fits:
                break
            distance *= 1.10
        self._cameraAspect = camera.lens.get_aspect_ratio()

    def setupLighting(self):
        # Soft overall fill light so black shadows aren't pitch dark
        ambient = AmbientLight(color=color.rgba(100, 100, 100, 255))
        
        # Main sun light angled down to create clear top & side contrast
        sun = DirectionalLight(shadows=True)
        sun.look_at(Vec3(1, -2, -1))  # Angled light source
    
    def renderBoard(self, board=None):
        """Reads gameModel.board grid and spawns 3D floor tiles."""
        board = self.gameModel.board if board is None else board
        self.effectTileEntities = []

        closed = {p for key, positions in board.bridgeGroups.items()
                  if not board.bridgeState[key] for p in positions}
        for r in range(board.rows):
            for c in range(board.cols):
                tileType = board.getTile(r, c)
                if tileType == Tile.GOAL:
                    # One recessed goal, unlike unmarked VOID gaps. The root
                    # owns its rim/bottom so board redraw removes every part.
                    goal = Entity(name='goal_hole', position=(c, -0.1, -r))
                    self.tileEntities.append(goal)
                    for x, z, width, depth in ((-0.47, 0, 0.04, 0.98),
                                               (0.47, 0, 0.04, 0.98),
                                               (0, -0.47, 0.90, 0.04),
                                               (0, 0.47, 0.90, 0.04)):
                        Entity(name='goal_rim', parent=goal, model='cube',
                               position=(x, 0, z), scale=(width, 0.2, depth),
                               color=color.lime, texture='white_cube')
                    Entity(name='goal_bottom', parent=goal, model='cube',
                           position=(0, -0.4, 0), scale=(0.90, 0.08, 0.90),
                           color=color.dark_gray)
                    continue
                if tileType != Tile.VOID or (r, c) in closed:
                    # c = X axis (columns), r = Z axis (rows)
                    tileEntity = Entity(
                        model='cube',
                        color=color.dark_gray if (r,c) in closed else self.tileColors.get(tileType, color.white),
                        position=(c, -0.3 if (r,c) in closed else -0.1, -r),
                        scale=(0.92, 0.04 if (r,c) in closed else 0.2, 0.92),
                        texture='white_cube'      # Adds built-in subtle edge shadowing
                    )
                    self.tileEntities.append(tileEntity)
                    if tileType in (Tile.FRAGILE, Tile.SOFT_SWITCH, Tile.HEAVY_SWITCH,
                                    Tile.SPLIT_SWITCH, Tile.BRIDGE) or (r, c) in closed:
                        self.effectTileEntities.append(tileEntity)
                    labels = {Tile.SOFT_SWITCH: "o", Tile.HEAVY_SWITCH: "X", Tile.SPLIT_SWITCH: "( )"}
                    if tileType in labels:
                        label = labels[tileType] + ('!' if (r,c) in board.fatalCloseSwitches | board.fatalSplitSwitches else '')
                        marker = Text(text=label, parent=tileEntity, origin=(0,0),
                                      rotation=(90,0,0), y=0.6, scale=3, color=color.black)
                        # Parent destruction removes the marker too.

    def animateFall(self, direction: Direction = None):
        """Start falling only after the arrival and board-effect phase."""
        self.isAnimating = True
        handles = []
        for mesh, _, _ in self.visualSnapshot():
            handles.append(mesh.animate_y(mesh.y - 10, duration=1, curve=curve.in_cubic))
        if self.blockMesh.enabled and direction in (Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT):
            if direction in (Direction.UP, Direction.DOWN):
                angle = -60 if direction == Direction.UP else 60
                handles.append(self.blockMesh.animate_rotation_x(self.blockMesh.rotation_x + angle, duration=0.5))
            else:
                angle = 60 if direction == Direction.LEFT else -60
                handles.append(self.blockMesh.animate_rotation_z(self.blockMesh.rotation_z + angle, duration=0.5))
        def fallen():
            self._movement = None
            self.schedule(self.restartLevel, 0.1)
        self.watchAnimations(handles, fallen)

    def updateBlockMesh(self, block=None):
        """
        Reads gameModel.block state and updates 3D mesh position and scale.
        Accounts for detaching roll math base positions.
        """
        currentBlock = self.gameModel.block if block is None else block
        split = currentBlock.orientation == Orientation.SPLIT
        self.blockMesh.enabled = not split
        for index, mesh in enumerate(getattr(self, "cubeMeshes", [])):
            mesh.enabled = split
            if split:
                r, c = currentBlock.cubes[index]
                mesh.position = (c, 0, -r)
                mesh.scale = (0.9, 0.9, 0.9)
                mesh.color = color.yellow if index == currentBlock.active else color.azure
        if split:
            return
        r, c = currentBlock.r, currentBlock.c
        dr, dc = currentBlock.dr, currentBlock.dc
        targetScale = (0, 0, 0)
        targetPos = (0, 0, 0)

        if currentBlock.orientation == Orientation.STANDING:
            # Standing vertically: 1x2x1 scale, centered directly over tile (c, r)
            targetScale = (0.9, 1.8, 0.9)
            targetPos = (c, 0, -r)

        elif currentBlock.orientation == Orientation.LYING:
            if dc == 1:
                # Lying horizontally across columns c and c+1
                # Center point is c + 0.5 along X axis
                targetScale = (1.9, 0.9, 0.9)
                targetPos = (c + 0.5, 0, -r)

            elif dr == 1:
                # Lying vertically across rows r and r+1
                # Center point is r + 0.5 along Z axis
                targetScale = (0.9, 0.9, 1.9)
                targetPos = (c, 0, -(r + 0.5))

        # Apply scale 
        self.blockMesh.scale = targetScale
        self.blockMesh.position = targetPos

    def handleUrsinaInput(self, key: str):
        """Pass key to InputHandler, then update 3D mesh if state changed."""

        if not self.gameStarted:
            return
        uti = self.inputHandler.processKeyUtility(key)
        if uti is not None:
            match uti:
                case Utility.PAUSE:
                    self.togglePause()
                case Utility.RESTART:
                    self.restartLevel()
            return

        # Block game inputs if game hasn't started, is paused, or animation is playing
        if not self.gameStarted or self.isPaused or self.isAnimating or self.isSolving:
            return

        dir = self.inputHandler.processKeyDirection(key)

        if dir is None:
            return
        if dir == Direction.SWITCH and self.gameModel.block.orientation != Orientation.SPLIT:
            return

        self.beginMove(dir)

    def beginMove(self, action):
        """Compute the transition once and immediately present its final pose."""
        if self.isAnimating or self.gameModel.hasWon or getattr(self, "_presentingMove", False):
            return False
        self.isAnimating = True
        valid = self.gameModel.executeMove(action)
        if not valid and not self.gameModel.isGameOver:
            self.isAnimating = self.isSolving = False
            self.solverMessage.text = "Replay/input error: invalid move"
            return False
        self._presentingMove = True
        self.finishStep(action)
        return True

    def schedule(self, callback, delay):
        generation = getattr(self, "_animationGeneration", 0)
        holder = [None]
        def guarded():
            if generation != getattr(self, "_animationGeneration", 0):
                return
            call = holder[0]
            if call is not None and call in self._pendingCalls:
                self._pendingCalls.remove(call)
            callback()
        if not hasattr(self, "_pendingCalls"):
            self._pendingCalls = []
        call = invoke(guarded, delay=delay)
        holder[0] = call
        if call is not None:
            self._pendingCalls.append(call)
        return call

    def visualSnapshot(self):
        meshes = ([self.blockMesh] if hasattr(self, "blockMesh") else []) + getattr(self, "cubeMeshes", [])
        return [(m, tuple(m.position), tuple(m.scale)) for m in meshes if m.enabled]

    def watchAnimations(self, handles, callback):
        generation = getattr(self, "_animationGeneration", 0)
        def complete():
            if generation == getattr(self, "_animationGeneration", 0):
                callback()
        self._movement = AnimationCompletion(handles, complete)

    def updateAnimations(self, delta=None):
        if hasattr(self, '_cameraAspect') and abs(camera.lens.get_aspect_ratio()-self._cameraAspect) > 1e-4:
            self.setupCamera()
        blackout = getattr(self, '_blackoutRemaining', None)
        if blackout is not None:
            elapsed = max(0.0, getattr(time, 'dt', 0.0) if delta is None else delta)
            self._blackoutRemaining = max(0.0, blackout - elapsed)
            if self._blackoutRemaining <= 1e-9:
                self._blackoutRemaining = None
                self.loadNextLevel()
            return
        remaining = getattr(self, '_fatalRemaining', None)
        if remaining is not None:
            elapsed = max(0.0, getattr(time, 'dt', 0.0) if delta is None else delta)
            self._fatalRemaining = max(0.0, remaining - elapsed)
            if self._fatalRemaining > 1e-9:
                self.setFatalMessage(f'{self._fatalTitle}\nLoss in {ceil(self._fatalRemaining)} s')
            else:
                self._fatalRemaining = None
                self.setFatalMessage('YOU LOSE\nRestarting...')
                self.schedule(self.restartLevel, 1.0)
            return
        movement = getattr(self, "_movement", None)
        if movement is not None:
            movement.poll()  # Only asynchronous effects, currently falling.
        if getattr(self, "_replayReady", False) and not self.isAnimating:
            elapsed = getattr(time, 'dt', 0.0) if delta is None else delta
            self._replayRemaining = max(0.0, getattr(self, "_replayRemaining", 0.0) - elapsed)
            if self._replayRemaining > 1e-9:
                return
            self._replayReady = False
            self.playSolution()  # At most one action here per frame; no recursion.

    def queueReplay(self):
        if self.isSolving:
            self._replayReady = True

    def finishStep(self, direction=None):
        if not getattr(self, "_presentingMove", False):
            return  # Duplicate/stale completion cannot repeat win/fall handling.
        self._presentingMove = False
        self.updateBlockMesh()
        self.destroyTileEntities()
        self.renderBoard()
        if self.gameModel.isGameOver:
            self.isSolving = self._replayReady = False
            if self.gameModel.board.fatalSwitch is not None:
                self.isAnimating = True
                self._fatalRemaining = 5.0
                self._fatalTitle = ('Split trap!' if self.gameModel.board.fatalSwitch in
                                    self.gameModel.board.fatalSplitSwitches else 'Permanent CLOSE!')
                self.setFatalMessage(f'{self._fatalTitle}\nLoss in 5 s')
            else:
                self.animateFall(direction)
        elif self.gameModel.hasWon:
            self.startWinTransition()
        else:
            self.isAnimating = False

    def setFatalMessage(self, message):
        self._fatalNotice = True
        self.solverMessage.text = message.replace('\n', ' ')
        overlay = getattr(self, 'fatalMessage', None)
        if overlay is not None:
            overlay.text, overlay.enabled = message, True

    def startWinTransition(self):
        if not self.gameModel.hasWon or getattr(self, '_winPhase', None) is not None:
            return
        self._winPhase = 'fall'
        self.isAnimating = True
        self.isSolving = self._replayReady = False
        handle = self.blockMesh.animate_y(-3.5, duration=0.6, curve=curve.in_cubic)
        self.watchAnimations([handle], self.finishWinFall)

    def finishWinFall(self):
        if getattr(self, '_winPhase', None) != 'fall':
            return
        movement = getattr(self, '_movement', None)
        if movement is not None and not movement.completed:
            return
        self._movement = None
        self.blockMesh.enabled = False
        self._winPhase = 'collapse'
        self._winTilePoses = [(tile, tuple(tile.position), tuple(tile.scale), tile.enabled)
                             for tile in getattr(self, 'tileEntities', [])]
        visible = [pose for pose in self._winTilePoses if pose[3]]
        if not visible:
            self.finishBoardCollapse()
            return
        block = self.gameModel.block
        distances = [abs(p[0]-block.c) + abs(p[2]+block.r) for _, p, _, _ in visible]
        furthest = max(max(distances), 1.0)
        handles = []
        for (tile, position, scale, _), distance in zip(visible, distances):
            delay = 0.32 * distance / furthest
            handles.append(tile.animate_y(position[1]-6, duration=0.28, delay=delay,
                                          resolution=10, curve=curve.in_quad))
            handles.append(tile.animate_scale(tuple(v*0.05 for v in scale), duration=0.16,
                                               delay=delay+0.1, resolution=6, curve=curve.in_quad))
        self.watchAnimations(handles, self.finishBoardCollapse)

    def finishBoardCollapse(self):
        if getattr(self, '_winPhase', None) != 'collapse':
            return
        movement = getattr(self, '_movement', None)
        if movement is not None and not movement.completed:
            return
        self._movement = None
        for tile, _, _, _ in self._winTilePoses:
            tile.enabled = False
        self._winPhase = 'blackout'
        self._blackoutRemaining = 1.0
        self.winBlackout.enabled = True

    def run(self):
        """Starts the main Ursina 3D render loop."""

        # Keep Ursina's dispatcher intact: it normalizes keys and routes events
        # to menus, mouse handling, and entities on both press and release.
        self.inputEntity = Entity(input=self.handleUrsinaInput, update=self.updateAnimations)
        self.app.run()

    def solve(self, algorithm):
        """Search an isolated snapshot and replay on the matching live state."""
        if self.isAnimating:
            return
        self.isSolving = True
        self.problem = Problem(State(self.gameModel.board, self.gameModel.block).copy())
        try:
            result = run_search(self.problem, algorithm, SearchLimits(), heuristic=None)
            validate_solution(self.problem, result.search)
        except NotImplementedError as exc:
            self.solverMessage.text = str(exc)
            print(exc)
            self.isSolving = False
            return
        except Exception as exc:
            self.solverMessage.text = f"Solver error: {exc}"
            self.isSolving = False
            print(f"Solver error: {exc}")
            return
        self.solverMessage.text = (f"{algorithm}: {result.search.status}; moves={len(result.search.actions)} "
                                   f"cost={result.search.total_cost}\n"
                                   f"{result.search_time_seconds:.3f}s; {result.peak_memory_bytes} bytes; "
                                   f"expanded={result.search.expanded_nodes}")
        print(result)
        if result.search.status != "solved":
            self.isSolving = False
            return
        self.autoSolution = list(result.search.actions)
        self.autoIndex = 0
        self._replayCall = self.schedule(self.queueReplay, 0.5)

    def cancelReplay(self):
        was_winning = getattr(self, '_winPhase', None) is not None
        self._winPhase = self._blackoutRemaining = None
        blackout = getattr(self, 'winBlackout', None)
        if blackout is not None:
            blackout.enabled = False
        if getattr(self, '_fatalNotice', False):
            self.solverMessage.text = ''
        self._fatalNotice = False
        self._fatalRemaining = None
        overlay = getattr(self, 'fatalMessage', None)
        if overlay is not None:
            overlay.enabled = False
        self._animationGeneration = getattr(self, "_animationGeneration", 0) + 1
        movement = getattr(self, "_movement", None)
        if movement is not None:
            movement.cancel()
        self._movement = None
        for tile, position, scale, enabled in getattr(self, '_winTilePoses', []):
            for animation in list(tile.animations):
                animation.kill()
            tile.position, tile.scale, tile.enabled = position, scale, enabled
        self._winTilePoses = []
        self._presentingMove = self._replayReady = False
        self._replayRemaining = 0.0
        calls = list(getattr(self, "_pendingCalls", []))
        if getattr(self, "_replayCall", None):
            calls.append(self._replayCall)
        for call in calls:
            if call:
                call.kill()
        self._pendingCalls = []
        self._replayCall = None
        for mesh in ([self.blockMesh] if hasattr(self, "blockMesh") else []) + getattr(self, "cubeMeshes", []):
            for animation in list(mesh.animations):
                animation.kill()
            mesh.rotation = (0, 0, 0)
        self.autoSolution = []
        self.autoIndex = 0
        self.isSolving = self.isAnimating = False
        if was_winning:
            self.updateBlockMesh()

    def playSolution(self):
        if not self.isSolving or self.isAnimating:
            return

        if self.autoIndex >= len(self.autoSolution):
            self.isSolving = False
            print("Finished")
            if (self.gameModel.hasWon): 
                self.startWinTransition()
            return

        action = self.autoSolution[self.autoIndex]

        if self.beginMove(action):
            self.autoIndex += 1
            if self.isSolving and not self.isAnimating:
                self._replayRemaining = self.replayInterval
                self.queueReplay()

    def loadNextLevel(self):
        self.cancelReplay()

        # Load next level
        result = self.levelManager.nextLevel()

        if result is None:
            print("Finished all levels")
            self.solverMessage.text = 'All levels completed!'
            self.isAnimating = False
            return

        self.changeLevel(result)

    def changeLevel(self, result):
        self.cancelReplay()
        self.pauseMenu.disable()
        self.solverMenu.hide()
        board, block = result

        # Replace current level
        self.gameModel.board = board
        self.gameModel.block = block

        # Reset game state
        self.gameModel.hasWon = False
        self.gameModel.isGameOver = False

        # Clear old board
        self.destroyTileEntities()

        # Camera may need to move if board size changed
        self.setupCamera()

        # Draw new board
        self.renderBoard()

        # Reset block mesh
        self.blockMesh.rotation = (0, 0, 0)
        self.updateBlockMesh()

        # Unlock controls
        self.unlockControlAll()
        self.problem = Problem(
            State(
                self.gameModel.board,
                self.gameModel.block
            )
        )
