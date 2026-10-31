from gameModel.block import Direction, Orientation
from gameModel.rules import transition, winning


class Problem:
    def __init__(self, initialState):
        self.initial = initialState

    def goal_test(self, state):
        return winning(state)

    def actions(self, state):
        return [a for a in Direction if a != Direction.SWITCH or state.block.orientation == Orientation.SPLIT]

    def result(self, state, action):
        child, valid, _ = transition(state, action)
        return child if valid else None

    def step_cost(self, state, action, nextState):
        # Mọi bước đi (kể cả SWITCH) đều có chi phí 1.
        return 1.0