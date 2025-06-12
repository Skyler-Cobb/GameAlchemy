"""
AssetManager  –  now size‑aware.

It caches each (filename, size) pair separately so we never upscale a
thumbnail; every unique size is rendered directly from the source file once.
"""
from __future__ import annotations
from pathlib import Path
import pygame

class AssetManager:
    def __init__(self, covers_dir: Path):
        self.covers_dir = covers_dir
        # key = (filename, size‑tuple or None)  -> pygame.Surface
        self._cache: dict[tuple[str, tuple[int,int]|None], pygame.Surface] = {}

    # ----------------------------------------------------------------
    def get_icon(self, filename: str, size: tuple[int, int] | None) -> pygame.Surface:
        """
        Return a Surface of the requested size.
        If *size* is None the original raster size is returned.
        """
        key = (filename, size)
        if key in self._cache:
            return self._cache[key]

        path = self.covers_dir / filename
        try:
            surf = pygame.image.load(path).convert_alpha()
        except Exception:
            # fallback = coloured square if the file can’t load
            colour = [(180,50,50),(50,180,50),(50,50,180),
                      (200,120,40),(180,50,180),(50,180,180),(180,180,50)
                     ][hash(filename)%7]
            surf = pygame.Surface((256,256), pygame.SRCALPHA)
            surf.fill(colour)

        if size is not None:
            surf = pygame.transform.smoothscale(surf, size)

        self._cache[key] = surf
        return surf
