from game.snake import Snake
from game.food import RegularFood, BonusFood
from game.tracker import HandTracker
from game.utils import FingerSnakeGame

if __name__ == "__main__":
    game = FingerSnakeGame()
    game.run()
