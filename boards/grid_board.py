"""
GridBoard – a generic, tile‑based play‑field.

Used by:
    • BrickLayer (tetris clone) – tall matrix, gravity, etc.
    • Snake             – wrap or clamp movement, food spawning
    • Minesweeper       – static mines + reveal/flag states
    • Pipeline          – node routing / pipe drawing
    • Pairs             – flipping card pairs

The board itself does *no* game rules; it only:
    1. Manages a 2‑D array of "cells" (dicts by default).
    2. Converts between (row, col) <‑‑> pixel coordinates.
    3. Provides convenience drawing helpers.
"""
from __future__ import annotations
from typing import Callable, Any, Tuple, List
import pygame

class GridBoard:
    def __init__(
        self,
        rows: int,
        cols: int,
        cell_size: int = 32,
        origin: Tuple[int, int] = (0, 0),
        cell_factory: Callable[[], Any] | None = None,
    ):
        self.rows      = rows
        self.cols      = cols
        self.cell_size = cell_size
        self.origin    = origin
        self._factory  = cell_factory or (lambda: {})
        self.grid: List[List[Any]] = [
            [self._factory() for _ in range(cols)] for _ in range(rows)
        ]

        # cached surfaces for lines
        self._grid_surf = self._build_grid_surface()

    # ───────────────────────────── geometry ──────────────────────────
    def cell_to_pixel(self, row: int, col: int) -> Tuple[int, int]:
        ox, oy = self.origin
        return ox + col * self.cell_size, oy + row * self.cell_size

    def pixel_to_cell(self, x: int, y: int) -> Tuple[int, int] | None:
        ox, oy = self.origin
        col = (x - ox) // self.cell_size
        row = (y - oy) // self.cell_size
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return row, col
        return None

    # ─────────────────────────── rendering ───────────────────────────
    def _build_grid_surface(self) -> pygame.Surface:
        w = self.cols * self.cell_size
        h = self.rows * self.cell_size
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        # draw grid lines once
        c = (80, 80, 80)
        for r in range(self.rows + 1):
            y = r * self.cell_size
            pygame.draw.line(surf, c, (0, y), (w, y), width=1)
        for cidx in range(self.cols + 1):
            x = cidx * self.cell_size
            pygame.draw.line(surf, c, (x, 0), (x, h), width=1)
        return surf

    def draw(self, target: pygame.Surface) -> None:
        target.blit(self._grid_surf, self.origin)

    # ───────────────────────── game‑loop stubs ───────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        """Override or use externally; grid itself needs no input."""
        pass

    def update(self, dt: float) -> None:
        """Per‑frame hook (e.g. Snake movement, Tetris gravity)."""
        pass
