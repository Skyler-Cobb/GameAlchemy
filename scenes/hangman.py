# scenes/hangman.py
"""
Hangman scene for GameAlchemy.

Word lists (placed in `data/`):
    • hangman-1.txt  → Easy
    • hangman-2.txt  → Normal
    • hangman-3.txt  → Hard
    • hangman-4.txt  → Expert
Each file contains one term per line.  Multi-word terms are allowed; spaces in
the answer appear as already-revealed gaps between underscores.
"""

from __future__ import annotations
import random, time
from pathlib import Path
from typing import Dict, List, Set

import pygame

from boards.word_board import WordBoard
from config            import WIDTH, HEIGHT, PROJECT_ROOT
from constants         import MENU_BG_COLOR
from ui.widgets        import Button

# ─────────── difficulty ↔ word-list filenames ────────────
DIFFICULTY_FILES: Dict[str, str] = {
    "Easy":   "hangman-1.txt",
    "Normal": "hangman-2.txt",
    "Hard":   "hangman-3.txt",
    "Expert": "hangman-4.txt",
}
MAX_MISTAKES = 7                        # 0..7 SVG frames

# keyboard-feedback colours
MISS_CLR = ( 70,  70,  70)              # dark grey
HIT_CLR  = (118, 210, 118)              # light green


# ─────────────────────── word-list helpers ────────────────────────
_WORD_CACHE: Dict[str, List[str]] = {}

def _load_word_list(diff: str) -> List[str]:
    """Lazy-load and cache the list for a given difficulty."""
    if diff in _WORD_CACHE:
        return _WORD_CACHE[diff]

    fname = DIFFICULTY_FILES[diff]
    path  = PROJECT_ROOT / "data" / fname
    with path.open(encoding="utf-8") as f:
        # Upper-case, strip trailing whitespace, ignore blank lines
        words = [ln.rstrip("\n").upper() for ln in f if ln.strip()]
    if not words:
        raise ValueError(f"No words found in {fname}")
    _WORD_CACHE[diff] = words
    return words


def _choose_word(diff: str) -> str:
    return random.choice(_load_word_list(diff))


# ─────────────────────────── scene class ──────────────────────────
class HangmanScene:
    def __init__(self, screen: pygame.Surface, difficulty_name: str = "Normal"):
        self.screen      = screen
        self.difficulty  = difficulty_name

        # pick a word / phrase
        self.word = _choose_word(self.difficulty)          # e.g. "IRON MAN"
        self.revealed: List[bool] = [
            (ch == " ") for ch in self.word                # spaces start revealed
        ]
        self.guessed:  Set[str] = set()
        self.mistakes  = 0
        self.game_over = False
        self.win       = False

        # fonts
        pygame.font.init()
        self.title_f = pygame.font.Font(None, 52)
        self.word_f  = pygame.font.Font(None, 78)
        self.hud_f   = pygame.font.Font(None, 32)

        # gallows frames
        g_dir = PROJECT_ROOT / "assets" / "gameparts" / "gallows"
        self.gallows = []
        for i in range(MAX_MISTAKES + 1):
            img  = pygame.image.load(g_dir / f"gallows-{i}.svg").convert_alpha()
            scale = 280 / img.get_height()
            img  = pygame.transform.smoothscale(img, (int(img.get_width()*scale), 280))
            self.gallows.append(img)

        # WordBoard (keyboard only)
        kb_size, kb_gap = 40, 6
        self.board = WordBoard(guesses=0, word_len=max(10, len(self.word.replace(" ", ""))),
                               slot_size=kb_size, gap=kb_gap, origin=(0, 0))
        kb_w, kb_h = self.board._keyboard_surf.get_size()
        # reserve 70 px for end-screen buttons + 20 px margin
        self.board.origin = ((WIDTH - kb_w)//2, HEIGHT - kb_h - 90)

        # per-letter key colours
        self.key_colours: Dict[str, tuple[int,int,int]] = {}

        # end-screen buttons
        self.restart_btn: Button | None
        self.back_btn = None
        self._build_buttons()

        # timer
        self.start_time = time.time()
        self.elapsed    = 0.0

    # ───────── helpers ─────────
    def _build_buttons(self):
        if not self.game_over:
            self.restart_btn = self.back_btn = None
            return
        w, h, cx = 160, 50, WIDTH//2
        y = HEIGHT - h - 20
        self.restart_btn = Button(pygame.Rect(cx-w-20, y, w, h), "Restart")
        self.back_btn    = Button(pygame.Rect(cx+20,   y, w, h), "Back")

    def _reveal(self, ch: str):
        for i, c in enumerate(self.word):
            if c == ch:
                self.revealed[i] = True

    def _guess(self, ch: str):
        if self.game_over or ch in self.guessed: return
        ch = ch.upper()
        if not ch.isalpha(): return          # ignore anything not A-Z
        self.guessed.add(ch)

        if ch in self.word:
            self._reveal(ch)
            self.key_colours[ch] = HIT_CLR
            if all(self.revealed): self.win = self.game_over = True
        else:
            self.key_colours[ch] = MISS_CLR
            self.mistakes += 1
            if self.mistakes >= MAX_MISTAKES: self.game_over = True
        self._build_buttons()

    def _reset(self): self.__init__(self.screen, self.difficulty)

    # ───────── event loop ─────────
    def handle_event(self, ev: pygame.event.Event):
        if self.game_over:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.restart_btn and self.restart_btn.hovered(ev.pos): self._reset(); return
                if self.back_btn    and self.back_btn.hovered(ev.pos):    return "menu"
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE: return "menu"
                if ev.key == pygame.K_r:      self._reset(); return
            return

        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE: return "menu"
        if ev.type == pygame.KEYDOWN and ev.unicode.isalpha():      self._guess(ev.unicode)
        if ev.type == pygame.USEREVENT and hasattr(ev, "letter"):   self._guess(ev.letter)
        self.board.handle_event(ev)

    # ───────── update ─────────
    def update(self, dt: float):
        if not self.game_over:
            self.board.update(dt)
            self.elapsed = time.time() - self.start_time

    # ───────── draw helpers ─────────
    def _draw_word(self):
        chars = []
        for i, ch in enumerate(self.word):
            if ch == " ":
                chars.append(" ")
            elif self.revealed[i] or (self.game_over and not self.win):
                chars.append(ch)
            else:
                chars.append("_")
        label = self.word_f.render(" ".join(chars), True, (255,255,255))
        self.screen.blit(label, label.get_rect(midtop=(WIDTH//2, 60)))

    def _draw_keyboard_feedback(self):
        if not self.key_colours: return
        ox, oy = self.board.origin
        kb_y   = oy + 30               # keyboard block top inside WordBoard
        for ch, colour in self.key_colours.items():
            rect = self.board._keyboard_rects[ch].inflate(-4,-4).move(ox, kb_y)
            pygame.draw.rect(self.screen, colour, rect, border_radius=6)
            lbl = self.board.font.render(ch, True, (255,255,255))
            self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    # ───────── main draw ─────────
    def draw(self):
        self.screen.fill(MENU_BG_COLOR)

        title = ("You Win!" if self.win else "You Lose!") if self.game_over else "Hangman"
        t_lbl = self.title_f.render(title, True, (255,255,255))
        self.screen.blit(t_lbl, t_lbl.get_rect(midtop=(WIDTH//2, 10)))

        self.screen.blit(self.hud_f.render(self.difficulty, True, (255,255,255)),
                         self.hud_f.render("x",True,(0,0,0)).get_rect(topright=(WIDTH-10,15)))
        self.screen.blit(self.hud_f.render(f"{int(self.elapsed):03d}s",True,(255,255,255)), (10,15))

        self.screen.blit(self.gallows[min(self.mistakes, MAX_MISTAKES)],
                         (WIDTH//2 - self.gallows[0].get_width()//2, 120))
        self._draw_word()

        if not self.game_over:
            self.board.draw(self.screen)
            self._draw_keyboard_feedback()

        if self.game_over:
            if self.restart_btn: self.restart_btn.draw(self.screen)
            if self.back_btn:    self.back_btn.draw(self.screen)


# ───────────────────────── registry hook ───────────────────────────
def register(registry):
    def launch(scr: pygame.Surface, **kw):
        return HangmanScene(scr, difficulty_name=kw.get("difficulty_name","Normal"))
    registry.register("Hangman", "hangman.svg",
                      launcher=launch,
                      difficulties={name: {"difficulty_name": name}
                                    for name in DIFFICULTY_FILES})
