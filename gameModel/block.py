from enum import Enum

class Orientation(Enum):
    STANDING = 1
    LYING = 2

class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4



class Block:
    def __init__(self, r: int, c: int, dr: int = 0, dc: int = 0,
                 orientation = Orientation.STANDING):

        # The base position of the Block, it should be the position with
        # The lowest value for both r and c among the occupied positions
        # Leftmost part when lying horizontally and top part when lying vertically
        self.r = r
        self.c = c

        # The offset from the base position
        self.dr = dr
        self.dc = dc

        # Whether the Block is standing or lying flat
        self.orientation = orientation
    
    def __repr__(self):
        return f"Block(r = {self.r}, c = {self.c}, orientation = '{self.orientation.name}', dr = '{self.dr}', dc = '{self.dc}')"
    
    # Returns a copy of the Block so the original instance will not be modified when 
    # Searching for a solution
    def copy(self):
        return Block(self.r, self.c, self.dr, self.dc, self.orientation)

    def __eq__(self, other):
        if not isinstance(other, Block): return False
        return (self.r, self.c, self.dr, self.dc, self.orientation) == (other.r, other.c, other.dr, other.dc, other.orientation)

    def __hash__(self):
        return hash((self.r, self.c, self.dr, self.dc, self.orientation))

    
    def resultingState(self, dir: Direction) -> "Block":
        """
        Creates a new instance of Block after applying the action
        To be used in search algorithms for the solver
        """
        r, c = self.r, self.c
        if (self.orientation == Orientation.STANDING):
            match dir:
                case Direction.UP:    return Block(r - 2, c, 1, 0, Orientation.LYING)
                case Direction.DOWN:  return Block(r + 1, c, 1, 0, Orientation.LYING)
                case Direction.LEFT:  return Block(r, c - 2, 0, 1, Orientation.LYING)
                case Direction.RIGHT: return Block(r, c + 1, 0, 1, Orientation.LYING)

        elif self.orientation == Orientation.LYING:
            # Check dr/dc to distinguish horizontal vs vertical lying states
            if self.dc == 1:
                # When the Block is lying horizontally
                match dir:
                    case Direction.UP:    return Block(r - 1, c, 0, 1, Orientation.LYING)
                    case Direction.DOWN:  return Block(r + 1, c, 0, 1, Orientation.LYING)
                    case Direction.LEFT:  return Block(r, c - 1, 0, 0, Orientation.STANDING)
                    case Direction.RIGHT: return Block(r, c + 2, 0, 0, Orientation.STANDING)

            elif self.dr == 1:
                # When the Block is lying vertically
                match dir:
                    case Direction.UP:    return Block(r - 1, c, 0, 0, Orientation.STANDING)
                    case Direction.DOWN:  return Block(r + 2, c, 0, 0, Orientation.STANDING)
                    case Direction.LEFT:  return Block(r, c - 1, 1, 0, Orientation.LYING)
                    case Direction.RIGHT: return Block(r, c + 1, 1, 0, Orientation.LYING)
                     

        raise ValueError(f"Invalid state or direction: {self}, {dir.name}")

    def applyMove(self, direction: Direction):
        """Helper to mutate this Block instance in-place."""
        nextBlock = self.resultingState(direction)
        self.r = nextBlock.r
        self.c = nextBlock.c
        self.dr = nextBlock.dr
        self.dc = nextBlock.dc
        self.orientation = nextBlock.orientation

    def moveUp(self):
        self.applyMove(Direction.UP)

    def moveDown(self):
        self.applyMove(Direction.DOWN)

    def moveLeft(self):
        self.applyMove(Direction.LEFT)

    def moveRight(self):
        self.applyMove(Direction.RIGHT)

###================================
### For testing
###================================

# myBlock = Block(0, 0)

# Block.moveDown(myBlock)
# print(Block.__repr__(myBlock))

# Block.moveRight(myBlock)
# print(Block.__repr__(myBlock))

# Block.moveUp(myBlock)
# print(Block.__repr__(myBlock))

# Block.moveLeft(myBlock)
# print(Block.__repr__(myBlock))
