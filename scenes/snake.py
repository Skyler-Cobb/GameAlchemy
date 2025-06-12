# scenes/snake.py
"""
Slim‑styled Snake scene for GameAlchemy
(15×15 board, four difficulties, 15‑item food cap, poison rules, etc.)

This version fixes the last visual glitch:
• Head now ends flush against the first body square (no extra length aft)
"""
from __future__ import annotations
import random, time
from collections import deque
from typing import Deque, Dict, List, Tuple

import pygame
from boards.grid_board import GridBoard
from config            import WIDTH, HEIGHT, PROJECT_ROOT
from constants         import MENU_BG_COLOR
from ui.widgets        import Button

# ─────────────────── gameplay constants ────────────────────────────
DIFFICULTIES = {
    "Easy":   {"speed": 4,  "apple_ratio": 1.00},
    "Normal": {"speed": 6,  "apple_ratio": 0.75},
    "Hard":   {"speed": 8,  "apple_ratio": 0.50},
    "Expert": {"speed": 12, "apple_ratio": 0.25},
}
HEAD_CLR, BODY_CLR            = (40, 220, 40), (30, 170, 30)
GRID_BG_CLR, GRID_BORDER_CLR  = (220, 220, 220), (60, 60, 60)
GRID_BORDER_W                 = 3
MAX_ITEMS_ON_BOARD            = 15
POISON_EXTRA_SPAWN            = 3.0
POISON_LIFETIME_MIN           = 10.0
POISON_LIFETIME_MAX           = 30.0


# ───────────────────────────── scene ───────────────────────────────
class SnakeScene:
    def __init__(
        self,
        screen: pygame.Surface,
        speed: float        = 6,
        apple_ratio: float  = 0.75,
        difficulty_name: str = "Normal",
    ):
        # state & grid
        self.screen = screen
        self.rows = self.cols = 15
        self.step_time   = 1.0 / speed
        self.apple_ratio = apple_ratio
        self.difficulty  = difficulty_name
        self.cs = min(32, (WIDTH - 20) // self.cols, (HEIGHT - 180) // self.rows)
        origin  = ((WIDTH - self.cols * self.cs) // 2, 80)
        self.board = GridBoard(self.rows, self.cols, self.cs, origin)

        # assets
        part = PROJECT_ROOT / "assets" / "gameparts"
        load = lambda svg: pygame.transform.smoothscale(
            pygame.image.load(part / svg).convert_alpha(), (self.cs, self.cs)
        )
        self.apple_img, self.poison_img = load("apple.svg"), load("apple_poison.svg")

        # fonts
        self.title_font = pygame.font.Font(None, 48)
        self.hud_font   = pygame.font.Font(None, 32)

        # segment thicknesses
        self.th_head = int(self.cs * 0.80)
        self.th_body = int(self.cs * 0.60)
        self.half_head = self.th_head // 2
        self.half_body = self.th_body // 2

        self._build_buttons()
        self._reset()

    # ───────────────────────── setup helpers ───────────────────────
    def _build_buttons(self):
        mid, y = WIDTH // 2, HEIGHT - 70
        self.restart_btn = Button(pygame.Rect(mid - 170, y, 150, 40), "Restart")
        self.back_btn    = Button(pygame.Rect(mid +  20, y, 180, 40), "Back to Menu")

    def _reset(self):
        mid = self.rows // 2
        self.snake: List[Tuple[int, int]] = [(mid, mid - 2), (mid, mid - 1), (mid, mid)]
        self.direction      = (0, 1)
        self.next_direction = self.direction
        self.poison_penalty = 1
        self.timer          = 0.0
        self.game_over      = False
        self.start_time     = time.time()
        self.elapsed_when_end = 0.0

        self.foods: List[Dict] = []
        self.spawn_queue: Deque[float] = deque()
        self._spawn_food()

    # ───────────────────────── grid helpers ────────────────────────
    def _cell_origin(self, r: int, c: int) -> Tuple[int, int]:
        return self.board.origin[0] + c * self.cs, self.board.origin[1] + r * self.cs

    def _cell_center(self, r: int, c: int) -> Tuple[int, int]:
        x, y = self._cell_origin(r, c)
        return x + self.cs // 2, y + self.cs // 2

    # ───────────────────────── spawning ────────────────────────────
    def _spawn_food(self):
        if len(self.foods) >= MAX_ITEMS_ON_BOARD:
            self.foods.pop(0)

        occupied = set(self.snake) | {f["pos"] for f in self.foods}
        free = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in occupied]
        if not free:
            return

        pos       = random.choice(free)
        is_poison = random.random() >= self.apple_ratio
        now       = time.time()
        self.foods.append({
            "pos": pos,
            "type": "poison" if is_poison else "apple",
            "despawn_at": now + random.uniform(POISON_LIFETIME_MIN, POISON_LIFETIME_MAX)
                          if is_poison else None,
        })
        if is_poison:
            self.spawn_queue.append(now + POISON_EXTRA_SPAWN)

    # ───────────────────── movement / rules ────────────────────────
    def _valid_turn(self, new: Tuple[int, int]) -> bool:
        return new != (-self.direction[0], -self.direction[1])

    def _step(self):
        if self.game_over:
            return
        self.direction = self.next_direction
        hr, hc = self.snake[-1]
        nr, nc = hr + self.direction[0], hc + self.direction[1]

        if (not 0 <= nr < self.rows) or (not 0 <= nc < self.cols) or ((nr, nc) in self.snake):
            self._end_game(); return

        self.snake.append((nr, nc))
        hit = next((f for f in self.foods if f["pos"] == (nr, nc)), None)
        if hit:
            self.foods.remove(hit)
            if hit["type"] == "apple":
                self.poison_penalty = 1
            else:
                if self.poison_penalty >= len(self.snake):
                    self._end_game(); return
                for _ in range(self.poison_penalty):
                    self.snake.pop(0)
                self.poison_penalty *= 2
            self._spawn_food()
        else:
            self.snake.pop(0)

    def _end_game(self):
        self.game_over = True
        self.elapsed_when_end = time.time() - self.start_time

    # ───────────────────────── event handling ──────────────────────
    def handle_event(self, ev: pygame.event.Event):
        if self.game_over:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.restart_btn.hovered(ev.pos): self._reset(); return
                if self.back_btn.hovered(ev.pos):    return "menu"
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return "menu"
            return

        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE: return "menu"
            dirs = {
                pygame.K_UP: (-1, 0), pygame.K_w: (-1, 0),
                pygame.K_DOWN: (1, 0), pygame.K_s: (1, 0),
                pygame.K_LEFT: (0, -1), pygame.K_a: (0, -1),
                pygame.K_RIGHT:(0, 1), pygame.K_d: (0, 1),
            }
            if ev.key in dirs and self._valid_turn(dirs[ev.key]):
                self.next_direction = dirs[ev.key]

    # ───────────────────────── update loop ─────────────────────────
    def update(self, dt: float):
        if self.game_over: return
        self.timer += dt
        while self.timer >= self.step_time:
            self.timer -= self.step_time
            self._step()

        now = time.time()
        self.foods[:] = [f for f in self.foods if not (f["type"] == "poison" and now >= f["despawn_at"])]
        while self.spawn_queue and self.spawn_queue[0] <= now:
            self.spawn_queue.popleft()
            self._spawn_food()

    # ───────────────────── drawing helpers ─────────────────────────
    def _bridge(self, p1: Tuple[int, int], p2: Tuple[int, int],
                thick: int, colour: Tuple[int, int, int], cut_back=False):
        """
        Draws rectangle from p1 to p2.
        If cut_back is True, the rectangle stops *before* reaching p2's centre
        by half the HEAD thickness. Used for neck→head join.
        """
        x1, y1 = p1
        x2, y2 = p2
        half   = thick // 2
        if cut_back:
            # shorten toward p2 by half_head along the direction vector
            if x1 == x2:       # vertical
                y2 -= self.direction[0] * self.half_head
            else:              # horizontal
                x2 -= self.direction[1] * self.half_head

        if y1 == y2:  # horizontal
            y = y1 - half
            x_start = min(x1, x2) - half
            width   = abs(x2 - x1) + thick
            pygame.draw.rect(self.screen, colour, (x_start, y, width, thick))
        else:         # vertical
            x = x1 - half
            y_start = min(y1, y2) - half
            height  = abs(y2 - y1) + thick
            pygame.draw.rect(self.screen, colour, (x, y_start, thick, height))

    # ───────────────────── drawing helpers ─────────────────────────
    def _draw_snake(self):
        """
        Draw body first, then head → head always appears on top.
        """
        centres = [self._cell_center(r, c) for r, c in self.snake]
        n       = len(centres)
        if n == 0:
            return

        head_c   = centres[-1]          # last element
        body_cs  = centres[:-1]         # everything except head

        # 1) BODY squares
        for cx, cy in body_cs:
            pygame.draw.rect(
                self.screen,
                BODY_CLR,
                pygame.Rect(cx - self.half_body, cy - self.half_body,
                            self.th_body, self.th_body),
            )

        # 2) BODY ↔ BODY bridges
        for i in range(1, n - 1):
            self._bridge(body_cs[i - 1], body_cs[i], self.th_body, BODY_CLR)

        # 3) NECK ↔ HEAD bridge (drawn with body thickness, trimmed)
        if body_cs:
            self._bridge(body_cs[-1], head_c, self.th_body, BODY_CLR, cut_back=True)

        # 4) HEAD square (draw last so it overlays the neck join)
        hx, hy = head_c
        pygame.draw.rect(
            self.screen,
            HEAD_CLR,
            pygame.Rect(hx - self.half_head, hy - self.half_head,
                        self.th_head, self.th_head),
        )

        # 5) HEAD forward half‑cell extension (also on top)
        dr, dc = self.direction
        extend = self.cs // 2 - self.half_head
        if dr:  # vertical
            x = hx - self.half_head
            y = hy + (self.half_head if dr > 0 else -self.half_head - extend)
            pygame.draw.rect(self.screen, HEAD_CLR, (x, y, self.th_head, extend))
        else:   # horizontal
            y = hy - self.half_head
            x = hx + (self.half_head if dc > 0 else -self.half_head - extend)
            pygame.draw.rect(self.screen, HEAD_CLR, (x, y, extend, self.th_head))

    # ───────────────────────────── draw ────────────────────────────
    def draw(self):
        self.screen.fill(MENU_BG_COLOR)
        board_rect = pygame.Rect(*self.board.origin, self.cols * self.cs, self.rows * self.cs)
        pygame.draw.rect(self.screen, GRID_BG_CLR, board_rect)
        pygame.draw.rect(self.screen, GRID_BORDER_CLR, board_rect, GRID_BORDER_W)
        self.board.draw(self.screen)

        for f in self.foods:
            img = self.apple_img if f["type"] == "apple" else self.poison_img
            self.screen.blit(img, self._cell_origin(*f["pos"]))

        self._draw_snake()

        elapsed = (time.time() - self.start_time) if not self.game_over else self.elapsed_when_end
        hud = self.hud_font.render(
            f"{self.difficulty}  |  Length: {len(self.snake)}  |  Time: {self._fmt(elapsed)}",
            True, (255, 255, 255))
        self.screen.blit(hud, hud.get_rect(center=(WIDTH // 2, 40)))

        if self.game_over:
            title = self.title_font.render("Game Over", True, (255, 60, 60))
            self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 70)))
            self.restart_btn.draw(self.screen)
            self.back_btn.draw(self.screen)

    # ────────────────────────── utilities ──────────────────────────
    @staticmethod
    def _fmt(sec: float) -> str:
        s = int(sec); h, s = divmod(s, 3600); m, s = divmod(s, 60)
        return f"{h:02}:{m:02}:{s:02}" if h else f"{m:02}:{s:02}"


# ─────────────────────── registry hook ─────────────────────────────
def register(registry):
    def launch(scr: pygame.Surface, **kw):
        opts = DIFFICULTIES.get(kw.get("difficulty_name", "Normal"), {})
        return SnakeScene(
            scr,
            speed         = kw.get("speed", opts.get("speed", 6)),
            apple_ratio   = kw.get("apple_ratio", opts.get("apple_ratio", 0.75)),
            difficulty_name = kw.get("difficulty_name", "Normal"),
        )

    diffs = {name: {**v, "difficulty_name": name} for name, v in DIFFICULTIES.items()}
    registry.register("Snake", "snake.svg", launcher=launch, difficulties=diffs)
