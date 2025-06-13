# scenes/wordit.py
"""
WordIt — Wordle-style mini-game for GameAlchemy (Normal & Hard).

Mouse-only controls via stacked DELETE/ENTER buttons (bottom-right).
"""

from __future__ import annotations
import random, time
from pathlib import Path
from typing import List, Dict, Tuple
import pygame

from boards.word_board import WordBoard
from config            import WIDTH, HEIGHT, PROJECT_ROOT
from constants         import MENU_BG_COLOR
from ui.widgets        import Button

# ───────── layout ─────────
WORD_LEN, MAX_TRIES = 5, 6
TILE, GAP           = 56, 8                 # ↓ 64 → 56 px tiles
GRID_W              = WORD_LEN*TILE + (WORD_LEN-1)*GAP
GRID_X, GRID_Y      = (WIDTH-GRID_W)//2, 60
GRID_BOTTOM         = GRID_Y + MAX_TRIES*TILE + (MAX_TRIES-1)*GAP

# ───────── palette ─────────
CLR_BG        = MENU_BG_COLOR
CLR_BORDER    = (120,120,120)
CLR_TEXT      = (255,255,255)
CLR_TEXT_FADE = (175,175,175)
CLR_CORRECT   = (118,210,118)
CLR_PRESENT   = (219,186, 60)
CLR_KEY_BASE  = (110,110,110)
CLR_KEY_USED  = ( 70, 70, 70)

# ───────── word list ─────────
_WORDS: List[str] | None = None
def _load_words()->List[str]:
    global _WORDS
    if _WORDS is None:
        path=PROJECT_ROOT/"data/words-5-letter.txt"
        with path.open(encoding="utf-8") as f:
            _WORDS=[ln.strip().upper() for ln in f if len(ln.strip())==WORD_LEN]
        if not _WORDS: raise ValueError("words-5-letter.txt missing/empty")
    return _WORDS

# ───────── scoring helper ─────────
def score_guess(ans:str, g:str)->List[str]:
    res,used=["absent"]*WORD_LEN,[False]*WORD_LEN
    for i,ch in enumerate(g):
        if ch==ans[i]: res[i]="correct"; used[i]=True
    for i,ch in enumerate(g):
        if res[i]=="correct": continue
        for j,a in enumerate(ans):
            if not used[j] and ch==a:
                res[i]="present"; used[j]=True; break
    return res

# ───────── scene ─────────
class WordItScene:
    def __init__(self, scr:pygame.Surface, mode:str="normal"):
        self.screen=scr
        self.hard_mode=mode.lower()=="hard"
        self.answer=random.choice(_load_words())
        self.guesses:List[str]=[]; self.results:List[List[str]]=[]
        self.current=""; self.game_over=False; self.win=False
        self.notice=""; self.notice_ts=0.0

        pygame.font.init()
        self.f_tile = pygame.font.Font(None, 56)   # matches 56-px tiles
        self.f_title= pygame.font.Font(None, 52)
        self.f_hud  = pygame.font.Font(None, 32)

        # keyboard
        kb_size,kb_gap=40,6
        self.kb=WordBoard(0,WORD_LEN,slot_size=kb_size,gap=kb_gap,origin=(0,0))
        kb_w,kb_h=self.kb._keyboard_surf.get_size()

        # bottom-right buttons
        BTN_W,BTN_H,BTN_GAP=140,50,8
        btn_x = WIDTH-BTN_W-20
        btn_enter_y = HEIGHT-BTN_H-20
        btn_del_y   = btn_enter_y-BTN_H-BTN_GAP
        self.enter_btn=Button(pygame.Rect(btn_x,btn_enter_y,BTN_W,BTN_H),"ENTER")
        self.del_btn  =Button(pygame.Rect(btn_x,btn_del_y,  BTN_W,BTN_H),"DELETE")

        # keyboard y-pos: 10 px under grid, or 10 px above DELETE – choose higher
        kb_y_under = GRID_BOTTOM + 20
        kb_y_above = btn_del_y   - kb_h + 50
        self.kb.origin = ((WIDTH-kb_w)//2, min(kb_y_under, kb_y_above))

        self.key_clr:Dict[str,Tuple[int,int,int]]={}
        self.restart_btn=self.back_btn=None
        self._build_end_buttons()

        self.start_time=time.time(); self.elapsed=0.0

    # ───────── utilities ─────────
    def _build_end_buttons(self):
        if not self.game_over:
            self.restart_btn = self.back_btn = None
            return
        w,h,cx = 160,50, WIDTH//2
        y = HEIGHT - h - 20
        self.restart_btn = Button(pygame.Rect(cx-w-20, y, w, h), "Restart")
        self.back_btn    = Button(pygame.Rect(cx+20,  y, w, h), "Back")

    def _state_of_key(self, ch: str) -> str | None:
        c = self.key_clr.get(ch)
        if c == CLR_CORRECT:  return "correct"
        if c == CLR_PRESENT:  return "present"
        if c == CLR_KEY_USED: return "absent"
        return None

    # ───────── hard-mode rule check ─────────
    def _validate_hard(self, guess: str) -> Tuple[bool,str]:
        greens: Dict[int,str] = {}
        yellows: set[str] = set()
        greys:   set[str] = set()

        for g, sc in zip(self.guesses, self.results):
            for idx, (ch, code) in enumerate(zip(g, sc)):
                if code == "correct":
                    greens[idx] = ch
                elif code == "present":
                    yellows.add(ch)
                elif code == "absent":
                    if ch not in greens.values() and ch not in yellows:
                        greys.add(ch)

        for idx, ch in greens.items():
            if guess[idx] != ch:
                return False, "Keep green letters in place"
        if not all(ch in guess for ch in yellows):
            return False, "Include all yellow letters"
        if any(ch in greys for ch in guess):
            return False, "Don't reuse grey letters"
        return True, ""

    def _notify(self, msg: str):
        self.notice, self.notice_ts = msg, time.time()

    # ───────── accept / reject guess ─────────
    def _submit(self):
        if len(self.current) != WORD_LEN:
            return
        g = self.current.upper()
        if not g.isalpha():
            return
        if self.hard_mode:
            ok, why = self._validate_hard(g)
            if not ok:
                self._notify(why); self.current = ""; return

        sc = score_guess(self.answer, g)
        self.guesses.append(g); self.results.append(sc)

        priority = {"absent":1,"present":2,"correct":3}
        for ch, code in zip(g, sc):
            if priority[code] > priority.get(self._state_of_key(ch) or "", 0):
                self.key_clr[ch] = (CLR_CORRECT if code=="correct"
                                    else CLR_PRESENT if code=="present"
                                    else CLR_KEY_USED)

        self.current = ""
        if g == self.answer: self.win = self.game_over = True
        elif len(self.guesses) >= MAX_TRIES: self.game_over = True
        self._build_end_buttons()

    def _reset(self):
        self.__init__(self.screen, "hard" if self.hard_mode else "normal")

    # ───────── event loop ─────────
    def handle_event(self, ev: pygame.event.Event):
        if self.game_over:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.restart_btn and self.restart_btn.hovered(ev.pos): self._reset(); return
                if self.back_btn and self.back_btn.hovered(ev.pos):       return "menu"
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_r, pygame.K_ESCAPE):
                if ev.key == pygame.K_r: self._reset()
                else: return "menu"
            return

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE: return "menu"
            if ev.key == pygame.K_RETURN: self._submit(); return
            if ev.key == pygame.K_BACKSPACE: self.current = self.current[:-1]
            elif ev.unicode.isalpha() and len(self.current) < WORD_LEN:
                self.current += ev.unicode.upper()

        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.enter_btn.hovered(ev.pos): self._submit(); return
            if self.del_btn.hovered(ev.pos):   self.current = self.current[:-1]; return

        if ev.type == pygame.USEREVENT and hasattr(ev, "letter"):
            if len(self.current) < WORD_LEN:
                self.current += ev.letter.upper()
        self.kb.handle_event(ev)

    def update(self, dt: float):
        if not self.game_over:
            self.kb.update(dt)
            self.elapsed = time.time() - self.start_time
        if self.notice and (time.time() - self.notice_ts > 2):
            self.notice = ""

    # ───────── drawing helpers ─────────
    def _tile_rect(self, r, c): return pygame.Rect(
        GRID_X + c*(TILE+GAP), GRID_Y + r*(TILE+GAP), TILE, TILE)

    def _blit(self, font, text, pos, col=CLR_TEXT):
        surf = font.render(text, True, col)
        self.screen.blit(surf, surf.get_rect(center=pos))

    # ───────── draw sections ─────────
    def _draw_grid(self):
        for r,(g,sc) in enumerate(zip(self.guesses, self.results)):
            for c,ch in enumerate(g):
                rect = self._tile_rect(r,c)
                col  = CLR_CORRECT if sc[c]=="correct" else CLR_PRESENT if sc[c]=="present" else CLR_KEY_USED
                pygame.draw.rect(self.screen, col, rect)
                pygame.draw.rect(self.screen, CLR_BORDER, rect, 2)
                fg = CLR_TEXT if col != CLR_KEY_USED else CLR_TEXT_FADE
                self._blit(self.f_tile, ch, rect.center, fg)
        r = len(self.guesses)
        if r < MAX_TRIES:
            for c in range(WORD_LEN):
                rect = self._tile_rect(r,c)
                pygame.draw.rect(self.screen, CLR_KEY_BASE, rect)
                pygame.draw.rect(self.screen, CLR_BORDER, rect, 2)
                if c < len(self.current):
                    self._blit(self.f_tile, self.current[c], rect.center)
        for rr in range(len(self.guesses)+1, MAX_TRIES):
            for cc in range(WORD_LEN):
                rect = self._tile_rect(rr,cc)
                pygame.draw.rect(self.screen, CLR_KEY_BASE, rect)
                pygame.draw.rect(self.screen, CLR_BORDER, rect, 2)

    def _draw_keyboard(self):
        self.kb.draw(self.screen)
        ox, oy = self.kb.origin; kb_y = oy + 30
        for ch, base in self.kb._keyboard_rects.items():
            if ch not in self.key_clr:
                rect = base.inflate(-4,-4).move(ox,kb_y)
                pygame.draw.rect(self.screen, CLR_KEY_BASE, rect, border_radius=6)
                pygame.draw.rect(self.screen, CLR_BORDER,   rect, 1, border_radius=6)
                self._blit(self.kb.font, ch, rect.center)
        for ch, col in self.key_clr.items():
            rect = self.kb._keyboard_rects[ch].inflate(-4,-4).move(ox,kb_y)
            pygame.draw.rect(self.screen, col, rect, border_radius=6)
            fg = CLR_TEXT if col != CLR_KEY_USED else CLR_TEXT_FADE
            self._blit(self.kb.font, ch, rect.center, fg)

    # ───────── main draw ─────────
    def draw(self):
        self.screen.fill(CLR_BG)
        title = ("You Win!" if self.win else
                 "You Lose!" if self.game_over else
                 ("WordIt – Hard" if self.hard_mode else "WordIt"))
        self._blit(self.f_title, title, (WIDTH//2, 25))
        if self.game_over and not self.win:
            self._blit(self.f_hud, f"Answer: {self.answer}", (WIDTH//2, 65))
        self.screen.blit(self.f_hud.render(f"{int(self.elapsed):03d}s",True,CLR_TEXT), (10,15))
        self._draw_grid()
        if self.notice:
            self._blit(self.f_hud, self.notice,
                       (WIDTH//2, GRID_BOTTOM + 50), CLR_PRESENT)
        if not self.game_over:
            self._draw_keyboard()
            self.del_btn.draw(self.screen); self.enter_btn.draw(self.screen)
        else:
            if self.restart_btn: self.restart_btn.draw(self.screen)
            if self.back_btn:    self.back_btn.draw(self.screen)


# ───────── registry hook ─────────
def register(registry):
    registry.register(
        "WordIt", "wordit.svg",
        launcher=lambda scr, **kw: WordItScene(scr, mode=kw.get("mode","normal")),
        difficulties={"Normal":{"mode":"normal"},
                      "Hard":{"mode":"hard"}}
    )
