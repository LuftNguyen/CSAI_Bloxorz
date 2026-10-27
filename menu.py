from ursina import Entity, Text, application, camera
from classic_theme import panel, bronze_button, GOLD, MUTED


class StartMenu(Entity):
    def __init__(self, on_start_callback):
        super().__init__(parent=camera.ui)
        self.on_start_callback = on_start_callback
        self.title = panel(self, 'BLOXORZ', height=.58)
        self.title.scale = 3.1
        Text(parent=self, text='C L A S S I C   E D I T I O N', origin=(0,0),
             y=.105, scale=.7, color=MUTED)
        self.start_button = bronze_button(self, 'START GAME', -.015, self.start_game)
        self.quit_button = bronze_button(self, 'QUIT', -.10, application.quit)
        Text(parent=self, text='A puzzle of balance and consequence.', origin=(0,0),
             y=-.225, scale=.65, color=MUTED)

    def start_game(self):
        self.disable()
        if self.on_start_callback:
            self.on_start_callback()


class PauseMenu(Entity):
    def __init__(self, on_resume_callback, on_restart_callback, on_next_level_callback, on_solver_callback):
        super().__init__(parent=camera.ui, enabled=False)
        self.on_resume_callback = on_resume_callback
        self.on_restart_callback = on_restart_callback
        self.on_next_level_callback = on_next_level_callback
        self.on_solver_callback = on_solver_callback
        self.title = panel(self, 'PAUSED', height=.75)
        self.resume_button = bronze_button(self, 'RESUME', .14, self.resume)
        self.restart_button = bronze_button(self, 'RESTART', .055, self.restart)
        self.next_level_button = bronze_button(self, 'NEXT LEVEL', -.03, self.nextLevel)
        self.solver_button = bronze_button(self, 'SOLVERS', -.115, self.solver)
        self.quit_button = bronze_button(self, 'QUIT GAME', -.20, application.quit)
        Text(parent=self, text='P TO RESUME', origin=(0,0), y=-.35, scale=.6, color=MUTED)

    def resume(self):
        self.disable()
        if self.on_resume_callback:
            self.on_resume_callback()

    def solver(self):
        self.disable()
        if self.on_solver_callback:
            self.on_solver_callback()

    def restart(self):
        self.disable()
        if self.on_restart_callback:
            self.on_restart_callback()

    def nextLevel(self):
        self.disable()
        if self.on_next_level_callback:
            self.on_next_level_callback()

    def toggle(self):
        self.enabled = not self.enabled


class SolverMenu(Entity):
    def __init__(self, algorithms, on_select, on_cancel):
        super().__init__(parent=camera.ui, enabled=False)
        self.algorithms, self.on_select = algorithms, on_select
        self.on_cancel = on_cancel
        self.elements = []
        self.create_menu()

    def create_menu(self):
        self.elements.append(panel(self, 'CHOOSE A SOLVER', height=.78))
        for index, name in enumerate(self.algorithms):
            def choose(algorithm=name):
                self.hide()
                self.on_select(algorithm)
            self.elements.append(bronze_button(self, name, .155-index*.085, choose))
        self.cancel_button = bronze_button(self, 'BACK TO GAME', -.205, self.on_cancel)
        Text(parent=self, text='P TO RESUME', origin=(0,0),
             y=-.32, scale=.6, color=MUTED)

    def show(self):
        self.enabled = True

    def hide(self):
        self.enabled = False
