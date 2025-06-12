# scenes/minesweeper.py
from __future__ import annotations
import pygame, random, time

from boards.grid_board import GridBoard
from config            import PROJECT_ROOT, WIDTH, HEIGHT
from constants         import MENU_BG_COLOR
from ui.widgets        import Button

# ───── difficulty presets ──────────────────────────────────────────
DIFFICULTIES = {
    "Easy":   {"rows": 9,  "cols": 9,  "mine_count": 10},
    "Normal": {"rows": 16, "cols": 16, "mine_count": 40},
    "Hard":   {"rows": 16, "cols": 25, "mine_count": 75},
    "Expert": {"rows": 16, "cols": 35, "mine_count": 100},
}

NUM_COLOURS = {
    1:(25,71,232), 2:(37,129,42), 3:(191,35,41), 4:(37,17,129),
    5:(144,19,19), 6:(17,140,140), 7:(0,0,0), 8:(128,128,128)
}

LIGHT_GRID_BG = (150,150,150)
LOSS_BG       = (255,180,180)   # light red tint under mines on loss

class MinesweeperScene:
    def __init__(self, screen: pygame.Surface,
                 rows:int, cols:int, mine_count:int,
                 difficulty_name:str="Normal"):
        self.screen=screen; self.rows, self.cols = rows, cols
        self.mine_count=mine_count; self.difficulty=difficulty_name

        # scale cell‑size
        self.cs=min(32,(WIDTH-20)//self.cols,(HEIGHT-180)//self.rows)
        origin=((WIDTH-self.cols*self.cs)//2,80)
        self.board=GridBoard(rows,cols,self.cs,origin)

        # assets
        part=PROJECT_ROOT/'assets'/'gameparts'
        def load(svg): return pygame.transform.smoothscale(
            pygame.image.load(part/svg).convert_alpha(),(self.cs,self.cs))
        self.tile_img=load('tile.svg')
        self.flag_img=load('flag.svg')
        self.mine_img=load('mine.svg')

        # fonts
        self.num_font  =pygame.font.Font(None,int(self.cs*0.8))
        self.title_font=pygame.font.Font(None,48)
        self.hud_font  =pygame.font.Font(None,32)

        self._reset_board()
        self.start_time:float|None=None; self.elapsed=0.0
        self.game_over=self.win=False
        self.restart_btn:Button|None=None
        self.back_btn:Button|None=None

    # ───────── helpers & setup ─────────────────────────────────────
    def _reset_board(self):
        self.first_click=True; self.game_over=self.win=False
        self.elapsed=0.0; self.start_time=None; self.exploded=None
        self.cells=[[{"mine":False,"adj":0,"rev":False,"flag":False}
                     for _ in range(self.cols)] for _ in range(self.rows)]

    def _place_mines(self,sr,sc):
        forbidden={(sr+dr,sc+dc)
                   for dr in(-1,0,1) for dc in(-1,0,1)
                   if 0<=sr+dr<self.rows and 0<=sc+dc<self.cols}
        pool=[(r,c) for r in range(self.rows) for c in range(self.cols)
              if (r,c) not in forbidden]
        for r,c in random.sample(pool,self.mine_count):
            self.cells[r][c]["mine"]=True
        for r in range(self.rows):
            for c in range(self.cols):
                if self.cells[r][c]["mine"]:continue
                self.cells[r][c]["adj"]=sum(
                    self.cells[r+dr][c+dc]["mine"]
                    for dr in(-1,0,1) for dc in(-1,0,1)
                    if 0<=r+dr<self.rows and 0<=c+dc<self.cols)

    def _pixel_to_cell(self,pos): return self.board.pixel_to_cell(*pos)

    def _flood(self,r0,c0):
        stack=[(r0,c0)]
        while stack:
            r,c=stack.pop()
            cd=self.cells[r][c]
            if cd["rev"]or cd["flag"]:continue
            cd["rev"]=True
            if cd["adj"]==0:
                for dr in(-1,0,1):
                    for dc in(-1,0,1):
                        nr,nc=r+dr,c+dc
                        if 0<=nr<self.rows and 0<=nc<self.cols:
                            stack.append((nr,nc))

    def _check_win(self):
        rev=sum(cd["rev"] for row in self.cells for cd in row)
        if rev==self.rows*self.cols-self.mine_count:
            self.win=self.game_over=True; self._build_buttons()

    def _build_buttons(self):
        mid=WIDTH//2; y=HEIGHT-70
        self.restart_btn=Button(pygame.Rect(mid-170,y,150,40),"Restart")
        self.back_btn   =Button(pygame.Rect(mid+20 ,y,180,40),"Back to Menu")

    @staticmethod
    def _fmt(sec:float)->str:
        s=int(sec); h,s=divmod(s,3600); m,s=divmod(s,60)
        return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"

    # ───────── event handling ──────────────────────────────────────
    def handle_event(self,ev:pygame.event.Event):
        if self.game_over:
            if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                if self.restart_btn and self.restart_btn.hovered(ev.pos): self._reset_board(); return
                if self.back_btn    and self.back_btn.hovered(ev.pos):    return "menu"
            if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: return "menu"
            return

        if ev.type==pygame.KEYDOWN and ev.key==pygame.K_ESCAPE: return "menu"

        if ev.type==pygame.MOUSEBUTTONDOWN and ev.button in(1,3):
            cell=self._pixel_to_cell(ev.pos)
            if not cell:return
            r,c=cell; cd=self.cells[r][c]

            if ev.button==3 and not cd["rev"]:
                cd["flag"]=not cd["flag"]; return

            if ev.button==1 and not cd["flag"]:
                if self.first_click:
                    self.first_click=False
                    self._place_mines(r,c)
                    self.start_time=time.time()
                if cd["mine"]:
                    cd["rev"]=True; self.exploded=(r,c)
                    self.game_over=True; self.win=False
                    self._build_buttons()
                else:
                    self._flood(r,c); self._check_win()

    # ───────── update & draw ───────────────────────────────────────
    def update(self,dt): 
        if not self.game_over and self.start_time:
            self.elapsed=time.time()-self.start_time

    def draw(self):
        self.screen.fill(MENU_BG_COLOR)
        # Title
        title="You Win!" if self.win else "You Lose!" if self.game_over else "Minesweeper"
        t_lbl=self.title_font.render(title,True,(255,255,255))
        self.screen.blit(t_lbl,t_lbl.get_rect(midtop=(WIDTH//2,10)))

        # HUD top
        self.screen.blit(self.hud_font.render(self._fmt(self.elapsed),True,(255,255,255)),(10,15))
        d_lbl=self.hud_font.render(self.difficulty,True,(255,255,255))
        self.screen.blit(d_lbl,d_lbl.get_rect(topright=(WIDTH-10,15)))

        # grid bg
        pygame.draw.rect(self.screen,LIGHT_GRID_BG,
                         (*self.board.origin,self.cols*self.cs,self.rows*self.cs))
        pygame.draw.rect(self.screen,(90,90,90),
                         (*self.board.origin,self.cols*self.cs,self.rows*self.cs),3)
        for r in range(1,self.rows):
            y=self.board.origin[1]+r*self.cs
            pygame.draw.line(self.screen,(200,200,200),
                             (self.board.origin[0],y),
                             (self.board.origin[0]+self.cols*self.cs,y))
        for c in range(1,self.cols):
            x=self.board.origin[0]+c*self.cs
            pygame.draw.line(self.screen,(200,200,200),
                             (x,self.board.origin[1]),
                             (x,self.board.origin[1]+self.rows*self.cs))

        lost=self.game_over and not self.win
        for r in range(self.rows):
            for c in range(self.cols):
                x,y=self.board.cell_to_pixel(r,c)
                cd=self.cells[r][c]
                if not cd["rev"]:
                    self.screen.blit(self.tile_img,(x,y))
                # tint lost mines
                if lost and cd["mine"]:
                    pygame.draw.rect(self.screen,LOSS_BG,(x,y,self.cs,self.cs))
                if cd["mine"] and (cd["rev"] or lost):
                    self.screen.blit(self.mine_img,(x,y))
                elif cd["rev"] and cd["adj"]>0 and not cd["mine"]:
                    col=NUM_COLOURS.get(cd["adj"],(255,255,255))
                    n_lbl=self.num_font.render(str(cd["adj"]),True,col)
                    self.screen.blit(n_lbl,n_lbl.get_rect(center=(x+self.cs//2,y+self.cs//2)))
                if cd["flag"]:
                    self.screen.blit(self.flag_img,(x,y))

        # HUD bottom
        flags=sum(cd["flag"] for row in self.cells for cd in row)
        f_lbl=self.hud_font.render(f"Mines Flagged: {flags}/{self.mine_count}",True,(255,255,255))
        self.screen.blit(f_lbl,(10,HEIGHT-40))
        rev=sum(cd["rev"] for row in self.cells for cd in row)
        prog=int(100*rev/(self.rows*self.cols-self.mine_count))
        p_lbl=self.hud_font.render(f"Progress: {prog:3d}%",True,(255,255,255))
        self.screen.blit(p_lbl,p_lbl.get_rect(bottomright=(WIDTH-10,HEIGHT-10)))

        if self.game_over:
            if self.restart_btn:self.restart_btn.draw(self.screen)
            if self.back_btn:self.back_btn.draw(self.screen)

# ───── register with GameRegistry ──────────────────────────────────
def register(registry):
    def launch(scr:pygame.Surface, **kw):
        return MinesweeperScene(
            scr,
            rows        = kw.get("rows",16),
            cols        = kw.get("cols",16),
            mine_count  = kw.get("mine_count",40),
            difficulty_name = kw.get("difficulty_name","Normal"),
        )
    diffs={n:{**v,"difficulty_name":n} for n,v in DIFFICULTIES.items()}
    registry.register("Minesweeper","minesweeper.svg",
                      launcher=launch, difficulties=diffs)
