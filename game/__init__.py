"""Package initializer for the game package.

This module provides a small, lazy convenience export so external code can
do::

	from game import FingerSnakeGame

without importing the heavier submodules at package import time. The lazy
import avoids circular import problems and keeps import time low.
"""

__version__ = "0.1"

__all__ = ["FingerSnakeGame"]

def __getattr__(name: str):
	if name == "FingerSnakeGame":
		from .utils import FingerSnakeGame

		return FingerSnakeGame
	raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

def __dir__():
	return sorted(__all__)
