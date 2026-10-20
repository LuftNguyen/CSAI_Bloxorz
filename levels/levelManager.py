from levels.levelLoader import loadLevelFromJson
from pathlib import Path


class LevelManager:

    def __init__(self):
        self.currentLevel = 1
        self.maxLevel = 11  # The source repository provides levels 1 through 11.


    def loadLevel(self):
        path = Path(__file__).parent / f"level{self.currentLevel}.json"

        return loadLevelFromJson(path)


    def nextLevel(self):

        if self.currentLevel < self.maxLevel:
            self.currentLevel += 1
            return self.loadLevel()

        print("All levels completed!")
        return None
