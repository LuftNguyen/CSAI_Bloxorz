from ursina import *

from gameModel.gameController import GameController
from gameModel.block import  Orientation, Direction
from gameModel.board import Tile
from inputHandler import InputHandler, Utility
from menu import *
from levels.levelManager import LevelManager

from runner import run_search
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
        self.solverMessage = Text(text="Team solvers: chua trien khai", x=-0.85, y=0.46, scale=0.8)

    def startGame(self):
        self.gameStarted = True
        self.tileColors = {
            Tile.NORMAL:       color.light_gray,
            Tile.GOAL:         color.magenta,
            Tile.FRAGILE:      color.orange,
            Tile.SOFT_SWITCH:  color.cyan,
            Tile.HEAVY_SWITCH: color.red,
            Tile.BRIDGE:       color.brown
        }

        self.tileEntities = []
        self.renderBoard()

        # 3D Block mesh creation
        self.blockMesh = Entity(
            model='cube',
            color=color.azure,
            texture='white_cube',   # Sharpens edges
            origin_y=-0.5  # Pivot at the bottom face of the block
        )
        self.updateBlockMesh()

    def showSolverMenu(self):
        if not self.gameStarted or not self.isPaused:
            return

        self.solverMenu.show()
        self.isPaused = False

    def handleAlgorithmSelected(self, algo_name: str):
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

    def restartLevel(self):
        """Resets the game model and refreshes 3D visual representations."""
        print("Restarting level...")

        self.cancelReplay()

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
        if not self.gameStarted:
            return
        self.isPaused = not self.isPaused
        self.pauseMenu.toggle()

    def setupCamera(self):
        board = self.gameModel.board
        
        # 1. Calculate true center X and Z of the board grid
        centerX = (board.cols - 1) / 2.0
        centerZ = -(board.rows - 1) / 2.0
        
        # 2. Determine the bounding size of the stage
        maxDim = max(board.cols, board.rows)
        
        # 3. Scale distance dynamically:
        # - Height (Y) grows with grid size
        # - Pull back along Z into negative space relative to the bottom edge (-board.rows)
        heightY = maxDim * 1.35
        distanceZ = -board.rows - (maxDim * 0.75)
        
        camera.position = (centerX, heightY, distanceZ)
        
        # 4. Point directly at the board center
        camera.look_at(Vec3(centerX, 0, centerZ))

    def setupLighting(self):
        # Soft overall fill light so black shadows aren't pitch dark
        ambient = AmbientLight(color=color.rgba(100, 100, 100, 255))
        
        # Main sun light angled down to create clear top & side contrast
        sun = DirectionalLight(shadows=True)
        sun.look_at(Vec3(1, -2, -1))  # Angled light source
    
    def renderBoard(self):
        """Reads gameModel.board grid and spawns 3D floor tiles."""
        board = self.gameModel.board

        for r in range(board.rows):
            for c in range(board.cols):
                tileType = board.getTile(r, c)
                if tileType != Tile.VOID:
                    # c = X axis (columns), r = Z axis (rows)
                    tileEntity = Entity(
                        model='cube',
                        color=self.tileColors.get(tileType, color.white),
                        position=(c, -0.1, -r),
                        scale=(0.92, 0.2, 0.92),
                        texture='white_cube'      # Adds built-in subtle edge shadowing
                    )
                    self.tileEntities.append(tileEntity)

    def animateFall(self, direction: Direction = None):
        """
        Drops the mesh down into the void from its current position
        """
        self.isAnimating = True
        fallDuration = 1

        # 1. Animate Y straight down into the void
        targetY = self.blockMesh.y - 10
        self.blockMesh.animate_y(
            targetY,
            duration=fallDuration,
            curve=curve.in_cubic
        )

        # 2. Add a slight tilt in the move direction so it doesn't drop completely flat
        if direction:
            match direction:
                case Direction.UP:    self.blockMesh.animate_rotation_x(self.blockMesh.rotation_x - 60, duration=fallDuration - 0.5)
                case Direction.DOWN:  self.blockMesh.animate_rotation_x(self.blockMesh.rotation_x + 60, duration=fallDuration - 0.5)
                case Direction.LEFT:  self.blockMesh.animate_rotation_z(self.blockMesh.rotation_z + 60, duration=fallDuration - 0.5)
                case Direction.RIGHT: self.blockMesh.animate_rotation_z(self.blockMesh.rotation_z - 60, duration=fallDuration - 0.5)

        # 3. Delay and trigger restartLevel
        invoke(lambda: self.restartLevel(), delay=fallDuration + 0.1)
    

    def updateBlockMesh(self):
        """
        Reads gameModel.block state and updates 3D mesh position and scale.
        Accounts for detaching roll math base positions.
        """
        currentBlock = self.gameModel.block
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
        print(f"KEY: '{key}'")

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

        self.gameModel.executeMove(dir)

        # Refresh board graphics
        # Important for bridge/switch changes
        self.destroyTileEntities()
        self.renderBoard()

        # Update block position
        self.updateBlockMesh()

        if self.gameModel.isGameOver or self.gameModel.hasWon:
            print("Updating mesh")

            if self.gameModel.hasWon:
                print("Stage Complete!")
                self.isAnimating = True
                invoke(self.loadNextLevel, delay=2)
                return

            elif self.gameModel.isGameOver:
                print("Game Over - Block fell into void!")
                self.isAnimating = True
                self.animateFall(dir)

    def run(self):
        """Starts the main Ursina 3D render loop."""

        # Pass the function directly into Ursina's app instance
        self.app.input = self.handleUrsinaInput
        self.app.run()

    def solve(self, algorithm):
        """Search an isolated snapshot and replay on the matching live state."""
        self.isSolving = True
        self.problem = Problem(State(self.gameModel.board, self.gameModel.block).copy())
        try:
            result = run_search(self.problem, algorithm, SearchLimits())
        except NotImplementedError as exc:
            self.solverMessage.text = str(exc)
            print(exc)
            self.isSolving = False
            return
        except Exception as exc:
            self.solverMessage.text = f"Solver error: {exc}"
            self.isSolving = False
            raise
        self.solverMessage.text = f"{algorithm}: {result.search.status}"
        print(result)
        if result.search.status != "solved":
            self.isSolving = False
            return
        self.autoSolution = list(result.search.actions)
        self.autoIndex = 0
        self._replayCall = invoke(self.playSolution, delay=0.5)

    def cancelReplay(self):
        if getattr(self, "_replayCall", None):
            self._replayCall.kill()
            self._replayCall = None
        self.autoSolution = []
        self.autoIndex = 0
        self.isSolving = False

    def playSolution(self):
        if not self.isSolving:
            return

        if self.autoIndex >= len(self.autoSolution):
            self.isSolving = False
            print("Finished")
            if (self.gameModel.hasWon): 
                self.loadNextLevel()
            return

        action = self.autoSolution[self.autoIndex]

        if not self.gameModel.executeMove(action):
            self.solverMessage.text = "Replay error: invalid move"
            self.isSolving = False
            return

        self.destroyTileEntities()

        self.renderBoard()

        self.updateBlockMesh()

        self.autoIndex += 1

        self._replayCall = invoke(self.playSolution, delay=0.4)

    def loadNextLevel(self):
        self.cancelReplay()

        # Load next level
        result = self.levelManager.nextLevel()

        if result is None:
            print("Finished all levels")
            self.isAnimating = False
            return

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