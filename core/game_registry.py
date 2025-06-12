# core/game_registry.py

from __future__ import annotations
import pygame
from typing import Dict, List, Tuple, Callable, Optional, Any

class GameRegistry:
    def __init__(self):
        # name → (cover_file, launcher_callable?, difficulties_mapping?)
        self._registry: Dict[str, Tuple[str, Optional[Callable[..., Any]], Optional[Dict[str, dict]]]] = {}

    def register(
        self,
        name: str,
        cover_file: str,
        launcher: Callable[..., Any] | None = None,
        difficulties: dict[str, dict] | None = None,
    ) -> None:
        """
        difficulties: mapping difficulty_name → kwargs dict for that game.
        """
        self._registry[name] = (cover_file, launcher, difficulties)

    def all_games(self) -> List[str]:
        return list(self._registry.keys())

    def cover_file(self, name: str) -> str:
        return self._registry[name][0]

    def launcher(self, name: str) -> Callable[..., Any] | None:
        return self._registry[name][1]

    def difficulties(self, name: str) -> dict[str, dict]:
        """Return the mapping of difficulty→kwargs, or empty dict."""
        diffs = self._registry[name][2]
        return diffs or {}

    def launch_game(
        self,
        name: str,
        screen: pygame.Surface,
        **kwargs: Any
    ) -> Any | None:
        """
        Call the registered launcher with screen and any kwargs (e.g. difficulty settings).
        """
        if name not in self._registry:
            print(f"[Registry] No such game: {name}")
            return None
        _, launcher, _ = self._registry[name]
        if not launcher:
            print(f"[Registry] No launcher defined for game: {name}")
            return None
        return launcher(screen, **kwargs)
