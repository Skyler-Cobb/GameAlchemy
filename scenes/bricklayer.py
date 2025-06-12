# scenes/bricklayer.py
"""
BrickLayer — GameAlchemy Tetris
───────────────────────────────
Controls
  ◀ / ▶  |  A / D : move
  ▲  |  W         : rotate clockwise
  Q               : rotate counter-clockwise
  ▼  |  S         : soft-drop (hold)
  Space           : hard-drop
  Esc             : back to menu
"""

from __future__ import annotations
import random, pygame
from typing import Dict, List, Tuple
from boards.grid_board import GridBoard
from config            import WIDTH, HEIGHT, PROJECT_ROOT
from constants         import MENU_BG_COLOR
from ui.widgets        import Button

# ───────── board & palette ─────────
ROWS, COLS             = 20, 10
GRID_BG_CLR            = (220, 220, 220)
GRID_BORDER_CLR        = (60,  60,  60)
GRID_BORDER_W          = 3

COLORS: Dict[str, Tuple[int,int,int]] = {
    "I": (  0, 255, 255), "J": (  0,   0, 255), "L": (255, 165,   0),
    "O": (255, 255,   0), "S": (  0, 255,   0), "T": (160,  32, 240),
    "Z": (255,   0,   0),
}

# ───────── difficulty & gravity ─────────
DIFFICULTIES = {
    # start-gravity , accel/sec
    "Easy":   (1.10, 0.0006),
    "Normal": (0.85, 0.0010),
    "Hard":   (0.65, 0.0015),
    "Expert": (0.45, 0.0022),
}
GRAVITY_MIN   = 0.05
SOFT_FACTOR   = 0.10          # soft-drop interval = gravity * factor

# ───────── shapes (auto-rotated) ─────────
def rot90(blocks: List[Tuple[int,int]]) -> List[Tuple[int,int]]:
    return [(-c, r) for r, c in blocks]

def rotations(base: List[Tuple[int,int]]) -> List[List[Tuple[int,int]]]:
    seq, seen = [], set()
    cur = base
    for _ in range(4):
        key = tuple(sorted(cur))
        if key not in seen:
            seq.append(cur); seen.add(key)
        cur = rot90(cur)
    return seq

BASE = {
    "I": [(-1,0),(0,0),(1,0),(2,0)],
    "J": [(-1,-1),(0,-1),(1,-1),(1,0)],
    "L": [(-1,0),(0,0),(1,0),(1,-1)],
    "O": [(0,0),(0,1),(1,0),(1,1)],
    "S": [(0,0),(0,1),(1,-1),(1,0)],
    "T": [(-1,0),(0,-1),(0,0),(0,1)],
    "Z": [(0,-1),(0,0),(1,0),(1,1)],
}
ROT = {k: rotations(v) for k,v in BASE.items()}

# ───────── scene class ─────────
class BrickLayerScene:
    def __init__(self, scr: pygame.Surface, difficulty_name="Normal"):
        self.scr  = scr
        self.diff = difficulty_name
        self.g0, self.g_acc = DIFFICULTIES[difficulty_name]

        # board geometry
        self.cs   = min(32, (WIDTH-20)//COLS, (HEIGHT-180)//ROWS)
        origin    = ((WIDTH - COLS*self.cs)//2, 80)
        self.rect = pygame.Rect(*origin, COLS*self.cs, ROWS*self.cs)
        self.grid = GridBoard(ROWS, COLS, self.cs, origin)

        # tile set
        tile = pygame.image.load(
            PROJECT_ROOT / "assets" / "gameparts" / "tile.svg"
        ).convert_alpha()
        tile = pygame.transform.smoothscale(tile, (self.cs, self.cs))
        self.tiles = {n:self._tint(tile,c) for n,c in COLORS.items()}

        # UI
        mid, y = WIDTH//2, HEIGHT-70
        self.btn_restart = Button(pygame.Rect(mid-170,y,150,40),"Restart")
        self.btn_menu    = Button(pygame.Rect(mid+ 20,y,180,40),"Back to Menu")
        self.font_big = pygame.font.Font(None,36)
        self.font_sml = pygame.font.Font(None,24)

        self._reset()

    # ───── helpers ─────
    @staticmethod
    def _tint(src: pygame.Surface, rgb: Tuple[int,int,int]) -> pygame.Surface:
        s = src.copy()
        mask = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        mask.fill((*rgb,255))
        s.blit(mask,(0,0), special_flags=pygame.BLEND_RGBA_MULT)
        return s

    def _spawn(self):
        t = random.choice(list(ROT))
        self.piece = {"type":t,"o":0,"row":0,"col":COLS//2}
        if not self._valid(self.piece):
            self.game_over=True

    # collision check
    def _valid(self,p)->bool:
        for dr,dc in ROT[p["type"]][p["o"]]:
            r,c=p["row"]+dr, p["col"]+dc
            if c<0 or c>=COLS or r>=ROWS: return False
            if r>=0 and self.cells[r][c]: return False
        return True

    # lock piece
    def _lock(self):
        t=self.piece["type"]
        for dr,dc in ROT[t][self.piece["o"]]:
            r,c=self.piece["row"]+dr, self.piece["col"]+dc
            if r>=0: self.cells[r][c]=t
            else:    self.game_over=True
        self._clear_lines()
        self._spawn()

    def _clear_lines(self):
        filled=[r for r in range(ROWS) if all(self.cells[r])]
        for r in reversed(filled): del self.cells[r]
        self.cells[0:0]=[[None]*COLS for _ in filled]
        if filled:
            self.lines+=len(filled)
            self.score+=(len(filled)**2)*100

    # ───── input ─────
    def handle_event(self,ev):
        if self.game_over:
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if self.btn_restart.hovered(ev.pos): self._reset(); return
                if self.btn_menu.hovered(ev.pos):    return "menu"
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE:
                return "menu"
            return

        if ev.type==pygame.KEYDOWN:
            if ev.key==pygame.K_ESCAPE: return "menu"

            if ev.key in (pygame.K_LEFT,pygame.K_a):  self._shift(-1)
            elif ev.key in (pygame.K_RIGHT,pygame.K_d): self._shift(+1)
            elif ev.key in (pygame.K_UP,pygame.K_w):  self._rotate(+1)
            elif ev.key==pygame.K_q:                  self._rotate(-1)

            elif ev.key in (pygame.K_DOWN,pygame.K_s):   # soft-drop start
                if not self.soft:
                    self._scale_timer(to_soft=True)
                    self.soft=True

            elif ev.key==pygame.K_SPACE:             # hard-drop
                while self._fall_one(): pass
                self._lock()

        elif ev.type==pygame.KEYUP and ev.key in (pygame.K_DOWN,pygame.K_s):
            if self.soft:
                self.soft=False
                self._scale_timer(to_soft=False)

    # shift / rotate
    def _shift(self,dx:int):
        nxt={**self.piece,"col":self.piece["col"]+dx}
        if self._valid(nxt): self.piece=nxt

    def _rotate(self,d:int):
        t=self.piece["type"]; n=len(ROT[t])
        nxt={**self.piece,"o":(self.piece["o"]+d)%n}
        for kick in (0,-1,1,-2,2):
            test={**nxt,"col":nxt["col"]+kick}
            if self._valid(test): self.piece=test; break

    # scale timer when toggling soft-drop
    def _scale_timer(self,to_soft:bool):
        old_step = self._cur_step(soft=not to_soft)
        new_step = self._cur_step(soft=to_soft)
        if old_step>0:
            self.timer *= new_step / old_step

    # fall one row
    def _fall_one(self)->bool:
        nxt={**self.piece,"row":self.piece["row"]+1}
        if self._valid(nxt):
            self.piece=nxt
            return True
        return False

    # per-frame update
    def _cur_step(self,soft:bool=None)->float: # type: ignore
        if soft is None: soft=self.soft
        base=max(self.g0 - self.g_acc*self.elapsed, GRAVITY_MIN)
        return base*SOFT_FACTOR if soft else base

    def update(self,dt:float):
        if self.game_over: return
        self.elapsed+=dt
        step=self._cur_step()
        self.timer+=dt
        while self.timer>=step:
            self.timer-=step
            if not self._fall_one():
                self._lock()
                break
            step=self._cur_step()  # step might shrink as gravity accelerates

    # ───── rendering ─────
    def draw(self):
        self.scr.fill(MENU_BG_COLOR)
        pygame.draw.rect(self.scr,GRID_BG_CLR,self.rect)
        pygame.draw.rect(self.scr,GRID_BORDER_CLR,self.rect,GRID_BORDER_W)
        self.grid.draw(self.scr)

        # settled
        for r in range(ROWS):
            for c,t in enumerate(self.cells[r]):
                if t: self.scr.blit(self.tiles[t],self.grid.cell_to_pixel(r,c))

        # active
        t=self.piece["type"]
        for dr,dc in ROT[t][self.piece["o"]]:
            r,c=self.piece["row"]+dr, self.piece["col"]+dc
            if r>=0: self.scr.blit(self.tiles[t],self.grid.cell_to_pixel(r,c))

        self.scr.blit(self.font_sml.render(f"Lines: {self.lines}",True,(250,250,250)),
                      (self.rect.right+20,self.rect.top))
        self.scr.blit(self.font_sml.render(f"Score: {self.score}",True,(250,250,250)),
                      (self.rect.right+20,self.rect.top+28))

        if self.game_over:
            txt=self.font_big.render("GAME OVER",True,(255,220,220))
            self.scr.blit(txt, txt.get_rect(center=(WIDTH//2,40)))
            self.btn_restart.draw(self.scr)
        self.btn_menu.draw(self.scr)

    # ───── reset ─────
    def _reset(self):
        self.cells=[[None]*COLS for _ in range(ROWS)]
        self.lines=self.score=0
        self.elapsed=self.timer=0.0
        self.soft=False
        self.game_over=False
        self._spawn()

# ───────── loader hook ─────────
def register(registry):
    def launch(scr:pygame.Surface,**kw):
        return BrickLayerScene(scr,kw.get("difficulty_name","Normal"))
    registry.register("BrickLayer","bricklayer.svg",launcher=launch,
                      difficulties={d:{} for d in DIFFICULTIES})
