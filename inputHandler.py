from gameModel.block import Direction
from enum import Enum

class Utility(Enum):
    PAUSE = 1
    RESTART = 2

class InputHandler:
    def __init__(self):

        # Supports standard strings & Linux Panda3D string formats
        self.keyMap = {
            'arrow_left': Direction.LEFT,
            'left arrow': Direction.LEFT,
            'a': Direction.LEFT,
            
            'arrow_right': Direction.RIGHT,
            'right arrow': Direction.RIGHT,
            'd': Direction.RIGHT,
            
            'arrow_up': Direction.UP,
            'up arrow': Direction.UP,
            'w': Direction.UP,
            
            'arrow_down': Direction.DOWN,
            'down arrow': Direction.DOWN,
            's': Direction.DOWN,

            'escape': Utility.PAUSE,
            'escape up': Utility.PAUSE,
            'p': Utility.PAUSE,
            'p up': Utility.PAUSE,

            'r': Utility.RESTART,
            'r up': Utility.RESTART
        }

    def processKeyDirection(self, key: str) -> Direction:
        # 1. Ignore release events
        if key.endswith(' up'):
            return None
        cleanKey = key

        if cleanKey in self.keyMap:
            value = self.keyMap[cleanKey]
            return value if isinstance(value, Direction) else None

        return None

    def processKeyUtility(self, key: str) -> Utility:
        if key in self.keyMap:
            value = self.keyMap[key]
            return value if isinstance(value, Utility) else None

        return None
