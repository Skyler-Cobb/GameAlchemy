"""
Expose the public board classes.
"""
from .grid_board import GridBoard
from .word_board import WordBoard        # a.k.a WordGameBoard

__all__ = ["GridBoard", "WordBoard"]
