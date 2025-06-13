# pyright: reportMissingImports=false
from __future__ import annotations

import io
import os
import random
from typing import Dict, List, Tuple, Optional

import pygame

from boards.grid_board import GridBoard
from config            import WIDTH, HEIGHT
from constants         import MENU_BG_COLOR


# ──────────────────────────── constants ────────────────────────────
DIFFICULTIES: Dict[str, Dict[str, int]] = {
    "Easy"   : {"rows": 5, "cols": 5, "pair_count": 4, "min_seg": 3},
    "Normal" : {"rows": 6, "cols": 6, "pair_count": 5, "min_seg": 4},
    "Hard"   : {"rows": 7, "cols": 7, "pair_count": 6, "min_seg": 4},
    "Extreme": {"rows": 9, "cols": 9, "pair_count": 8, "min_seg": 4},
}

PALETTE: List[Tuple[int, int, int]] = [
    (255,  90,  90), ( 90, 255,  90), ( 90,  90, 255), (255, 180,  25),
    (160,  32, 240), (  0, 255, 255), (255, 255,   0), (255, 105, 180),
]

# pastel cheat colours
CHEAT: List[Tuple[int, int, int]] = [
    (
        r + (255 - r) * 3 // 5,
        g + (255 - g) * 3 // 5,
        b + (255 - b) * 3 // 5,
    )
    for r, g, b in PALETTE
]

GAMEPARTS_DIR = os.path.join("assets", "gameparts")


# ──────────────────────────── helpers ────────────────────────────
class Cell:
    __slots__ = ("type", "color")

    def __init__(self, typ: str = "empty", color: Optional[int] = None):
        self.type  = typ      # "empty" | "node" | "pipe"
        self.color = color    # palette idx


# ──────────────────────────── scene ────────────────────────────
class PipelineScene:
    DIRS        = [(1, 0), (-1, 0), (0, 1), (0, -1)]        # D U R L
    DIR_LABELS  = ["D", "U", "R", "L"]

    # ───────── init ─────────
    def __init__(self, screen: pygame.Surface,
                 difficulty_name: str = "Normal") -> None:

        cfg = DIFFICULTIES[difficulty_name]
        self.screen   = screen
        self.diff     = difficulty_name
        self.rows     = cfg["rows"]
        self.cols     = cfg["cols"]
        self.pair_n   = cfg["pair_count"]
        self.min_seg  = cfg["min_seg"]

        margin  = 60
        self.cell_px = min(
            (HEIGHT - 2 * margin) // self.rows,
            (WIDTH  - 2 * margin) // self.cols,
        )
        ox = (WIDTH  - self.cols * self.cell_px) // 2
        oy = (HEIGHT - self.rows * self.cell_px) // 2 + 20

        self.board = GridBoard(
            self.rows, self.cols,
            cell_size=self.cell_px,
            origin=(ox, oy),
            cell_factory=Cell,
        )

        self._load_assets()
        self._init_state()
        self._generate_board()

        self.title_font = pygame.font.SysFont(None, 48)
        self.hud_font   = pygame.font.SysFont(None, 28)

    # ───────── graphics ─────────
    def _load_svg(self, fname: str) -> pygame.Surface:
        path = os.path.join(GAMEPARTS_DIR, fname)
        try:
            surf = pygame.image.load(path).convert_alpha()
        except pygame.error:
            import cairosvg  # type: ignore
            with open(path, "rb") as f:
                png = cairosvg.svg2png(
                    bytestring=f.read(),
                    output_width=self.cell_px,
                    output_height=self.cell_px,
                )
            surf = pygame.image.load(io.BytesIO(png)).convert_alpha()
        return pygame.transform.smoothscale(surf, (self.cell_px, self.cell_px))

    def _load_assets(self) -> None:
        self.pipe_svg = {
            "straight"    : self._load_svg("pipe-straight.svg"),
            "elbow"       : self._load_svg("pipe-elbow.svg"),
            "cap"         : self._load_svg("pipe-cap.svg"),
            "node_closed" : self._load_svg("pipe-node-closed.svg"),
            "node_open"   : self._load_svg("pipe-node-open.svg"),
        }
        self.flow_svg = {
            "straight"    : self._load_svg("flow-straight.svg"),
            "elbow"       : self._load_svg("flow-elbow.svg"),
            "cap"         : self._load_svg("flow-cap.svg"),
            "node_closed" : self._load_svg("flow-node-closed.svg"),
            "node_open"   : self._load_svg("flow-node-open.svg"),
        }
        self._tint_cache: Dict[Tuple[str, int], pygame.Surface] = {}

    def _tinted_flow(self, key: str, col: int) -> pygame.Surface:
        ck = (key, col)
        if ck in self._tint_cache:
            return self._tint_cache[ck]
        base   = self.flow_svg[key]
        tinted = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        tinted.fill(PALETTE[col])
        mask = base.copy()
        mask.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
        tinted.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        self._tint_cache[ck] = tinted
        return tinted

    # ───────── state helpers ─────────
    def _init_state(self) -> None:
        self.nodes: List[Tuple[int, int, int]]            = []
        self.solution:   Dict[int, List[Tuple[int, int]]] = {}
        self.paths_drawn: Dict[int, List[Tuple[int, int]]] = {}
        self.completed:  Dict[int, bool]                  = {}
        self.active_col: Optional[int]                    = None
        self.active_path: List[Tuple[int, int]]           = []
        self.dragging = self.win = False

    def _neighbors(self, rc: Tuple[int, int]) -> List[Tuple[int, int]]:
        r, c = rc
        return [
            (r + dr, c + dc)
            for dr, dc in self.DIRS
            if 0 <= r + dr < self.rows and 0 <= c + dc < self.cols
        ]

    # ───────── board generation ─────────
    def _generate_board(self) -> None:
        total = self.rows * self.cols
        assert self.pair_n * self.min_seg <= total

        while True:
            # choose segment lengths
            rem = total
            lengths: List[int] = []
            for i in range(self.pair_n, 0, -1):
                if i == 1:
                    lengths.append(rem)
                    break
                L = random.randint(self.min_seg, rem - self.min_seg * (i - 1))
                lengths.append(L)
                rem -= L

            used: set[Tuple[int, int]] = set()
            segments: List[List[Tuple[int, int]]] = []
            failed = False

            for L in lengths:
                for _ in range(200):
                    start = random.randrange(self.rows), random.randrange(self.cols)
                    if start in used:
                        continue
                    path = [start]
                    while len(path) < L:
                        opts = [n for n in self._neighbors(path[-1])
                                if n not in used and n not in path]
                        if not opts:
                            break
                        path.append(random.choice(opts))
                    if len(path) == L:
                        used.update(path)
                        segments.append(path)
                        break
                else:
                    failed = True
                    break
            if not failed:
                break

        # register
        for col, seg in enumerate(segments):
            self.solution[col] = seg
            for r, c in (seg[0], seg[-1]):
                tile = self.board.grid[r][c]
                tile.type, tile.color = "node", col
            self.nodes.extend([(*seg[0], col), (*seg[-1], col)])
            self.completed[col] = False

    # ───────── input ─────────
    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            return "menu"

        if self.win:
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                return "menu"
            return

        # start drag
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            cell = self.board.pixel_to_cell(*ev.pos)
            if cell:
                r, c = cell
                tile = self.board.grid[r][c]
                if tile.type == "node" and tile.color is not None:
                    col: int = tile.color
                    self.active_col  = col
                    self.dragging    = True
                    self.active_path = [(r, c)]

                    prev = self.paths_drawn.pop(col, [])
                    for pr, pc in prev:
                        t = self.board.grid[pr][pc]
                        if t.type == "pipe":
                            t.type, t.color = "empty", None

        # drag move
        elif ev.type == pygame.MOUSEMOTION and self.dragging:
            cell = self.board.pixel_to_cell(*ev.pos)
            if not cell:
                return
            r, c = cell
            lr, lc = self.active_path[-1]
            if abs(r - lr) + abs(c - lc) != 1:
                return

            tile = self.board.grid[r][c]

            # backtrack
            if (r, c) in self.active_path:
                idx = self.active_path.index((r, c))
                for rr, cc in self.active_path[idx + 1:]:
                    t = self.board.grid[rr][cc]
                    if t.type == "pipe":
                        t.type, t.color = "empty", None
                self.active_path = self.active_path[:idx + 1]
                return

            if tile.type in ("node", "pipe") and tile.color != self.active_col:
                return

            if tile.type == "empty":
                tile.type, tile.color = "pipe", self.active_col
            self.active_path.append((r, c))

        # end drag
        elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.dragging:
            self.dragging = False
            if not self.active_path or self.active_col is None:
                return

            col = self.active_col
            ends = [(r, c) for r, c, clr in self.nodes if clr == col]
            if self.active_path[-1] in ends and len(self.active_path) >= 2:
                self.paths_drawn[col] = self.active_path[:]
                self.completed[col]   = True
            else:
                for rr, cc in self.active_path[1:]:
                    t = self.board.grid[rr][cc]
                    if t.type == "pipe" and t.color == col:
                        t.type, t.color = "empty", None

            self.active_path.clear()
            self.active_col = None
            if self._all_connected_and_filled():
                self.win = True

    # ───────── logic helpers ─────────
    def _all_connected_and_filled(self) -> bool:
        filled = all(tile.type != "empty"
                     for row in self.board.grid for tile in row)
        return all(self.completed.values()) and filled

    def _center(self, r: int, c: int) -> Tuple[int, int]:
        x, y = self.board.cell_to_pixel(r, c)
        return x + self.cell_px // 2, y + self.cell_px // 2

    def _blit(self, surf: pygame.Surface, r: int, c: int, rot: int = 0) -> None:
        img = pygame.transform.rotate(surf, rot)
        ox, oy = self.board.origin
        self.screen.blit(img, (ox + c * self.cell_px, oy + r * self.cell_px))

    # ───────── sprite chooser (fixed) ─────────
    def _pipe_sprite(self, dirs: List[str]) -> Tuple[str, int]:
        """
        Decide which sprite to draw based on the exact directions present
        in the path *segment* (built from the direction-map, so never more
        than two).

        Returns (key, rotation_degrees).
        """
        if not dirs:
            return "straight", 0  # should never happen

        # endpoint (one neighbour)
        if len(dirs) == 1:
            rot = {"D": 0, "R": 90, "U": 180, "L": 270}[dirs[0]]
            return "cap", rot

        # two neighbours -------------------------------------------------
        s = frozenset(dirs)

        if s == {"U", "D"}:
            return "straight", 0
        if s == {"L", "R"}:
            return "straight", 90

        elbow_map = {
            frozenset({"D", "R"}): 0,
            frozenset({"R", "U"}): 90,
            frozenset({"U", "L"}): 180,
            frozenset({"L", "D"}): 270,
        }
        if s in elbow_map:
            return "elbow", elbow_map[s]

        # fallback (should not occur with valid paths)
        return "straight", 90

    # ───────── drawing ─────────
    DEBUG_PIPE_SPRITE = False   # ← set to True to print tracing info

    def _draw_pipes(self) -> None:
        dir_map = self._build_dir_map()  # build once per frame

        for r in range(self.rows):
            for c in range(self.cols):
                tile = self.board.grid[r][c]
                dirs = sorted(dir_map.get((r, c), []))  # might be []

                # PIPE -------------------------------------------------
                if tile.type == "pipe":
                    key, rot = self._pipe_sprite(dirs)

                    if self.DEBUG_PIPE_SPRITE and self.dragging:
                        print(f"pipe {(r,c)} {dirs} -> {key}@{rot}")

                    self._blit(self._tinted_flow(key, tile.color), r, c, rot)
                    self._blit(self.pipe_svg[key], r, c, rot)

                # NODE ------------------------------------------------
                elif tile.type == "node":
                    if dirs:
                        rot = {"U": 0, "L": 90, "D": 180, "R": 270}[dirs[0]]
                        self._blit(self._tinted_flow("node_open", tile.color), r, c, rot)
                        self._blit(self.pipe_svg["node_open"], r, c, rot)
                    else:
                        self._blit(self._tinted_flow("node_closed", tile.color), r, c)
                        self._blit(self.pipe_svg["node_closed"], r, c)

    def _draw_cheat(self) -> None:
        if not pygame.key.get_pressed()[pygame.K_p]:
            return
        width = max(2, self.cell_px // 4)
        for col, seg in self.solution.items():
            pts = [self._center(r, c) for r, c in seg]
            pygame.draw.lines(self.screen, CHEAT[col], False, pts, width)

    def draw(self) -> None:
        self.screen.fill(MENU_BG_COLOR)

        title = "Pipeline – " + self.diff if not self.win else "Perfect! Board filled!"
        lbl = self.title_font.render(title, True, (255, 255, 255))
        self.screen.blit(lbl, lbl.get_rect(midtop=(WIDTH // 2, 10)))

        self.screen.blit(self.board._grid_surf, self.board.origin)
        self._draw_pipes()
        self._draw_cheat()

        if self.win:
            hint = self.hud_font.render("Click anywhere to return", True, (255, 255, 255))
            self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 30)))

    def update(self, dt: float) -> None:
        pass  # static puzzle

    # ───────── path → direction map ─────────
    def _build_dir_map(self) -> Dict[Tuple[int, int], List[str]]:
        """
        Return { (r,c): [dir, …] } where dir in {'U','D','L','R'} enumerates
        *actual* predecessor/successor steps for every pipe cell.
        """
        dir_map: Dict[Tuple[int, int], List[str]] = {}

        def add(a: Tuple[int, int], b: Tuple[int, int]) -> None:
            ar, ac = a
            br, bc = b
            if ar == br:
                dir_ = "R" if bc > ac else "L"
            else:
                dir_ = "D" if br > ar else "U"
            dir_map.setdefault(a, []).append(dir_)
            # opposite for the neighbour
            opp = {"U": "D", "D": "U", "L": "R", "R": "L"}[dir_]
            dir_map.setdefault(b, []).append(opp)

        # committed paths
        for path in self.paths_drawn.values():
            for i in range(len(path) - 1):
                add(path[i], path[i + 1])

        # live path while dragging
        if self.dragging and self.active_path:
            for i in range(len(self.active_path) - 1):
                add(self.active_path[i], self.active_path[i + 1])

        return dir_map

# ───────────────────────── registry ─────────────────────────
def register(registry):
    registry.register(
        "Pipeline",
        "pipeline.svg",
        launcher=lambda scr, **kw: PipelineScene(scr, kw.get("difficulty_name", "Normal")),
        difficulties={d: {"difficulty_name": d} for d in DIFFICULTIES},
    )
