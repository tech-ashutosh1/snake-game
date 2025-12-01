import sys, os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # Running from inside .app or .exe
        return os.path.join(sys._MEIPASS, relative_path)
    # Running normally (VS Code / Terminal)
    return os.path.join(os.path.abspath("."), relative_path)

# Make the resource_path function globally available inside game modules
# (so utils, snake, audio, etc. can import it)
import builtins
builtins.resource_path = resource_path

# Import game modules AFTER setting resource_path
from game.snake import Snake
from game.food import RegularFood, BonusFood
from game.tracker import HandTracker
from game.utils import FingerSnakeGame

if __name__ == "__main__":
    game = FingerSnakeGame()
    game.run()

