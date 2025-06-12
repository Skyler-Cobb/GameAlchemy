# scenes/bricklayer.py
"""
BrickLayer — GameAlchemy Tetris
────────────────────────────────
Controls
  ◀▶ / A-D   : move
  ▲  /  W    : rotate (clockwise, SRS-pivot, always stays same piece)
  ▼  /  S    :   ▸ hold → soft-drop (≈ 10× faster)
                ▸ double-tap (<200 ms) → hard-drop
  ESC        : back to menu
"""

from __future__ import annotations
import pygame, random, time
from typing import Dict, List, Tuple
from boards.grid_board import GridBoard
from config            import WIDTH, HEIGHT, PROJECT_ROOT
from constants         import MENU_BG_COLOR
from ui.widgets        import Button

# ───────────────────────── geometry / palette ──────────────────────
ROWS, COLS             = 20, 10
GRID_BG_CLR            = (220, 220, 220)
GRID_BORDER_CLR        = (60,  60,  60)
GRID_BORDER_W          = 3

COLORS: Dict[str, Tuple[int,int,int]] = {
    "I": (  0, 255, 255),
    "J": (  0,   0, 255),
    "L": (255, 165,   0),
    "O": (255, 255,   0),
    "S": (  0, 255,   0),
    "T": (160,  32, 240),
    "Z": (255,   0,   0),
}

# ───────────────────────── difficulty profile ──────────────────────
DIFFICULTIES = {
    #   start-gravity    accel-per-sec
    "Easy":   (1.10, 0.0006),
    "Normal": (0.85, 0.0010),
    "Hard":   (0.65, 0.0015),
    "Expert": (0.45, 0.0022),
}
GRAVITY_MIN = 0.05              # cap

# ───────────────────────── shape generation ────────────────────────
def rot90(coords: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    """Rotate block offsets 90° clockwise around (0,0)."""
    return [(-c, r) for r,c in coords]

def build_rotations(base: List[Tuple[int,int]]) -> List[List[Tuple[int,int]]]:
    """Return the four unique CW rotations (some pieces dedupe later)."""
    rots = [base]
    for _ in range(3):
        nxt = rot90(rots[-1])
        rots.append(nxt)
    # remove duplicates (O, S, Z)
    unique = []
    for r in rots:
        if r not in unique:
            unique.append(r)
    return unique

BASE_SHAPES = {
    # (0,0) is the **pivot square** (SRS style)
    "I": [(-1,0),(0,0),(1,0),(2,0)],           # vertical at spawn
    "J": [(-1,-1),(0,-1),(1,-1),(1,0)],
    "L": [(-1,0),(0,0),(1,0),(1,-1)],
    "O": [(0,0),(0,1),(1,0),(1,1)],
    "S": [(0,0),(0,1),(1,-1),(1,0)],
    "T": [(-1,0),(0,-1),(0,0),(0,1)],
    "Z": [(0,-1),(0,0),(1,0),(1,1)],
}
ROTATIONS = {name: build_rotations(coords) for name,coords in BASE_SHAPES.items()}

# ───────────────────────── scene class ─────────────────────────────
class BrickLayerScene:
    HARD_DROP_WINDOW = 0.10      # seconds between taps that → slam

    def __init__(self, screen: pygame.Surface, difficulty_name="Normal"):
        self.scr  = screen
        self.diff = difficulty_name
        self.g0, self.g_acc = DIFFICULTIES[difficulty_name]

        # board sizing identical to other mini-games
        self.cs  = min(32, (WIDTH-20)//COLS, (HEIGHT-180)//ROWS)
        origin   = ((WIDTH - COLS*self.cs)//2, 80)
        self.br  = pygame.Rect(*origin, COLS*self.cs, ROWS*self.cs)
        self.grid = GridBoard(ROWS, COLS, self.cs, origin)

        # tint base tile once per piece
        tile_raw = pygame.image.load(
            PROJECT_ROOT / "assets" / "gameparts" / "tile.svg"
        ).convert_alpha()
        tile_raw = pygame.transform.smoothscale(tile_raw, (self.cs,self.cs))
        self.tiles = {n: self._tint(tile_raw, rgb) for n,rgb in COLORS.items()}

        # UI
        mid, y = WIDTH//2, HEIGHT-70
        self.btn_restart = Button(pygame.Rect(mid-170, y,150,40), "Restart")
        self.btn_menu    = Button(pygame.Rect(mid+ 20, y,180,40), "Back to Menu")
        self.f_big = pygame.font.Font(None, 36)
        self.f_sml = pygame.font.Font(None, 24)

        self._reset()

    @staticmethod
    def _tint(src: pygame.Surface, rgb: Tuple[int,int,int]) -> pygame.Surface:
        s = src.copy()
        mask = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        mask.fill((*rgb,255))
        s.blit(mask,(0,0), special_flags=pygame.BLEND_RGBA_MULT)
        return s

    # ─────────── gameplay helpers ───────────
    def _spawn(self):
        t = random.choice(list(ROTATIONS))
        self.piece = {"type":t, "o":0, "row":0, "col":COLS//2}
        if not self._valid(self.piece):
            self.game_over = True

    def _valid(self, p) -> bool:
        for dr,dc in ROTATIONS[p["type"]][p["o"]]:
            r,c = p["row"]+dr, p["col"]+dc
            if c<0 or c>=COLS or r>=ROWS:        # wall or floor
                return False
            if r>=0 and self.cells[r][c] is not None:
                return False
        return True

    def _lock(self):
        t = self.piece["type"]
        for dr,dc in ROTATIONS[t][self.piece["o"]]:
            r,c = self.piece["row"]+dr, self.piece["col"]+dc
            if r>=0:
                self.cells[r][c]=t
            else:
                self.game_over=True
        self._clr_lines()
        self._spawn()

    def _clr_lines(self):
        filled=[r for r in range(ROWS) if all(self.cells[r][c] for c in range(COLS))]
        if not filled: return
        for r in reversed(filled):
            del self.cells[r]
        self.cells[0:0] = [[None]*COLS for _ in range(len(filled))]
        self.lines += len(filled)
        self.score += (len(filled)**2)*100

    # ─────────── event handling ───────────
    def handle_event(self, ev):
        if self.game_over:
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if self.btn_restart.hovered(ev.pos): self._reset(); return
                if self.btn_menu.hovered(ev.pos):    return "menu"
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE:
                return "menu"
            return

        # gameplay keys
        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: return "menu"

            if ev.key in (pygame.K_LEFT, pygame.K_a):
                nxt={**self.piece,"col":self.piece["col"]-1}
                if self._valid(nxt): self.piece=nxt

            elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                nxt={**self.piece,"col":self.piece["col"]+1}
                if self._valid(nxt): self.piece=nxt

            elif ev.key in (pygame.K_UP, pygame.K_w):
                nxt={**self.piece,"o":(self.piece["o"]+1)%len(ROTATIONS[self.piece["type"]])}
                # basic wall-kicks
                for dx in (0,-1,1,-2,2):
                    test={**nxt,"col":nxt["col"]+dx}
                    if self._valid(test):
                        self.piece=test; break

            elif ev.key in (pygame.K_DOWN, pygame.K_s):
                now=time.time()
                if now-self.last_tap<=self.HARD_DROP_WINDOW:
                    # hard-drop
                    while self._valid({**self.piece,"row":self.piece["row"]+1}):
                        self.piece["row"]+=1
                    self._lock()
                    self.last_tap = 0         # reset combo
                else:
                    self.soft=True
                    self.last_tap=now
                self.down_held=True

        elif ev.type==pygame.KEYUP and ev.key in (pygame.K_DOWN, pygame.K_s):
            self.soft=False
            self.down_held=False

    # ─────────── update loop ───────────
    def update(self, dt: float):
        if self.game_over: return
        self.elapsed+=dt
        self.gravity=max(self.g0 - self.g_acc*self.elapsed, GRAVITY_MIN)
        step=self.gravity*0.1 if self.soft else self.gravity
        self.timer+=dt
        while self.timer>=step:
            self.timer-=step
            nxt={**self.piece,"row":self.piece["row"]+1}
            if self._valid(nxt):
                self.piece=nxt
            else:
                self._lock()

    # ─────────── rendering ───────────
    def draw(self):
        self.scr.fill(MENU_BG_COLOR)
        pygame.draw.rect(self.scr,GRID_BG_CLR,self.br)
        pygame.draw.rect(self.scr,GRID_BORDER_CLR,self.br,GRID_BORDER_W)
        self.grid.draw(self.scr)

        # settled
        for r in range(ROWS):
            for c in range(COLS):
                t=self.cells[r][c]
                if t:
                    self.scr.blit(self.tiles[t], self.grid.cell_to_pixel(r,c))

        # falling
        t=self.piece["type"]
        for dr,dc in ROTATIONS[t][self.piece["o"]]:
            r,c=self.piece["row"]+dr, self.piece["col"]+dc
            if r>=0:
                self.scr.blit(self.tiles[t], self.grid.cell_to_pixel(r,c))

        # HUD
        self.scr.blit(self.f_sml.render(f"Lines: {self.lines}",True,(250,250,250)),
                      (self.br.right+20,self.br.top))
        self.scr.blit(self.f_sml.render(f"Score: {self.score}",True,(250,250,250)),
                      (self.br.right+20,self.br.top+28))

        if self.game_over:
            txt=self.f_big.render("GAME OVER",True,(255,220,220))
            self.scr.blit(txt, txt.get_rect(center=(WIDTH//2,40)))
            self.btn_restart.draw(self.scr)
            self.btn_menu.draw(self.scr)
        else:
            self.btn_menu.draw(self.scr)

    # ─────────── reset ───────────
    def _reset(self):
        self.cells=[[None]*COLS for _ in range(ROWS)]
        self.lines=0; self.score=0
        self.elapsed=0.0; self.gravity=self.g0
        self.timer=0.0; self.soft=False
        self.down_held=False; self.last_tap=0.0
        self.game_over=False
        self._spawn()

# ───────────────────────── loader hook ─────────────────────────────
def register(registry):
    def launch(scr: pygame.Surface, **kw):
        return BrickLayerScene(scr, kw.get("difficulty_name","Normal"))
    registry.register("BrickLayer","bricklayer.svg", launcher=launch,
                      difficulties={d:{} for d in DIFFICULTIES})
