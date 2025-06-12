"""
WordBoard – utility surface that splits into:

  A) 'guess panel'  – rows × columns of letter slots
  B) on‑screen keyboard (QWERTY)

Games can colour individual keys/slots (e.g. Wordle greys/greens/yellows).

Provides hit‑testing so you can let players click the keyboard or just
listen to KEYDOWN events.
"""
from __future__ import annotations
from typing import Tuple, Dict, List
import pygame

class WordBoard:
    KEY_ROWS = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]

    def __init__(
        self,
        guesses: int = 6,
        word_len: int = 5,
        slot_size: int = 48,
        gap: int = 8,
        origin: Tuple[int, int] = (0, 0),
        font: pygame.font.Font | None = None,
    ):
        self.guesses   = guesses
        self.word_len  = word_len
        self.slot_size = slot_size
        self.gap       = gap
        self.origin    = origin
        self.font      = font or pygame.font.Font(None, slot_size - 10)

        # state
        self.grid: List[str] = ["" for _ in range(guesses)]   # current letters
        self.key_states: Dict[str, str] = {}  # letter -> "unset"/"miss"/"hit"/"close"

        # pre‑render static keyboard
        self._keyboard_rects: Dict[str, pygame.Rect] = {}
        self._keyboard_surf = self._build_keyboard_surface()

    # ───────────────────────── keyboard surface ──────────────────────
    def _build_keyboard_surface(self) -> pygame.Surface:
        row_h = self.slot_size + self.gap
        kb_w  = self.word_len * self.slot_size + (self.word_len - 1) * self.gap
        kb_h  = row_h * len(self.KEY_ROWS)
        surf  = pygame.Surface((kb_w, kb_h), pygame.SRCALPHA)

        y = 0
        for row in self.KEY_ROWS:
            # centre each row
            row_w = len(row) * self.slot_size + (len(row) - 1) * self.gap
            x = (kb_w - row_w) // 2
            for ch in row:
                rect = pygame.Rect(x, y, self.slot_size, self.slot_size)
                self._keyboard_rects[ch] = rect
                pygame.draw.rect(surf, (100, 100, 100), rect, width=2)
                label = self.font.render(ch, True, (220, 220, 220))
                surf.blit(label, label.get_rect(center=rect.center))
                x += self.slot_size + self.gap
            y += row_h
        return surf

    # ─────────────────────────── rendering ───────────────────────────
    def draw(self, target: pygame.Surface) -> None:
        ox, oy = self.origin
        # draw guess grid
        for r in range(self.guesses):
            y = oy + r * (self.slot_size + self.gap)
            for c in range(self.word_len):
                x = ox + c * (self.slot_size + self.gap)
                pygame.draw.rect(target, (200, 200, 200),
                                 (x, y, self.slot_size, self.slot_size), width=2)
                if c < len(self.grid[r]):
                    ch = self.grid[r][c]
                    label = self.font.render(ch, True, (240, 240, 240))
                    target.blit(label, label.get_rect(center=(x + self.slot_size//2,
                                                              y + self.slot_size//2)))
        # draw keyboard
        kb_y = oy + self.guesses * (self.slot_size + self.gap) + 30
        target.blit(self._keyboard_surf, (ox, kb_y))

    # ───────────────────────── hit testing ───────────────────────────
    def key_from_pos(self, pos: Tuple[int, int]) -> str | None:
        ox, oy = self.origin
        kb_y   = oy + self.guesses * (self.slot_size + self.gap) + 30
        rel    = (pos[0] - ox, pos[1] - kb_y)
        for ch, rect in self._keyboard_rects.items():
            if rect.collidepoint(rel):
                return ch
        return None

    # ───────────────────────── stubs for games ───────────────────────
    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Default implementation:
            - Click on keyboard produces a pygame.USEREVENT with attribute
              'letter' so your game scene can catch it.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            ch = self.key_from_pos(event.pos)
            if ch:
                evt = pygame.event.Event(pygame.USEREVENT, letter=ch)
                pygame.event.post(evt)

    def update(self, dt: float) -> None:
        pass
