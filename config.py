"""
Global constants shared across modules.
"""
import os
from pathlib import Path

# Window ---------------------------------------------------------------
WIDTH, HEIGHT = 900, 640
FPS           = 60
BG_COLOR      = (30, 30, 30)

# Fonts / sizes --------------------------------------------------------
import pygame  # only to query default font
FONT_NAME  = pygame.font.get_default_font()
ICON_SIZE  = (120, 120)
DROP_SIZE  = (340, 340)

# Assets ---------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent
COVERS_DIR   = PROJECT_ROOT / "assets" / "covers"

# Game list  (display‑name, cover‑file)
GAMES = [
    ("Minesweeper", "minesweeper.svg"),
    ("Snake",        "snake.svg"),
    ("BrickLayer",   "bricklayer.svg"),  # Tetris‑like
    ("Pipeline",     "pipeline.svg"),    # Flow‑like
    ("Hangman",      "hangman.svg"),
    ("Pairs",        "pairs.svg"),       # Concentration
    ("WordIt",       "wordit.svg"),      # Wordle‑like
]
