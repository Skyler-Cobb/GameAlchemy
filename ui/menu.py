"""
ui/menu.py

Main menu with:
 - Title banner
 - Trash (closed/open)
 - Drag-and-drop strip of game covers (horizontal scroll + scrollbar)
 - Combination box (single-double size) and PLAY/MIX buttons
 - Difficulty dropdown under PLAY (per-game)
"""

from __future__ import annotations
import pygame
from typing import Dict, List, Tuple, Any
from pathlib import Path

from config               import WIDTH, HEIGHT, FONT_NAME, ICON_SIZE, DROP_SIZE, PROJECT_ROOT
from constants            import (
    MENU_BG_COLOR, SCROLL_BG_COLOR, DROP_BORDER_COLOR,
    SCROLLBAR_TRACK_COLOR, SCROLLBAR_THUMB_COLOR,
    BUTTON_BG_COLOR, BUTTON_MIX_BG_COLOR,
    SCROLL_AREA_HEIGHT, SCROLLBAR_HEIGHT, ICON_SPACING, SCROLL_SPEED,
    TRASH_SIZE, TRASH_MARGIN,
    TITLE_MAX_W, TITLE_MARGIN_TOP,
)
from ui.widgets          import DraggableIcon, Button, Dropdown
from core.asset_manager  import AssetManager
from core.game_registry  import GameRegistry

# ────────────────────────────────────────────────────────────────────────
# All predefined mixes (extended)
COMBOS = {
    tuple(sorted(["pipeline", "minesweeper"])):    ("BombTech",     "bombtech.svg"),
    tuple(sorted(["hangman", "wordit"])):          ("Hangdle",      "hangdle.svg"),
    tuple(sorted(["minesweeper", "snake"])):       ("Minesnaker",   "minesnaker.svg"),
    tuple(sorted(["snake", "wordit"])):            ("Snurdle",      "snurdle.svg"),
    tuple(sorted(["wordit", "minesweeper"])):      ("Trigger Word", "triggerword.svg"),
    tuple(sorted(["minesweeper", "pairs"])):       ("Trap Card",    "trapcard.svg"),
    tuple(sorted(["minesweeper", "hangman"])):     ("Death Trap",   "deathtrap.svg"),
    tuple(sorted(["minesweeper", "bricklayer"])):  ("No Touching",  "notouching.svg"),
    tuple(sorted(["snake", "pairs"])):             ("Worm",         "worm.svg"),
    tuple(sorted(["snake", "bricklayer"])):        ("Statue Garden","statuegarden.svg"),
    tuple(sorted(["wordit", "bricklayer"])):       ("Word Salad",   "wordsalad.svg"),
    tuple(sorted(["pairs", "bricklayer"])):        ("Bailout",      "bailout.svg"),
}
COMBINED_NAMES = {name.lower() for name, _ in COMBOS.values()}

# ────────────────────────────────────────────────────────────────────────
class MenuUI:
    def __init__(self, screen: pygame.Surface, registry: GameRegistry, assets: AssetManager):
        self.screen   = screen
        self.registry = registry
        self.assets   = assets
        self.font     = pygame.font.Font(FONT_NAME, 18)

        # Title banner ------------------------------------------------------
        title_img      = pygame.image.load(PROJECT_ROOT / "assets" / "title.png").convert_alpha()
        scale_ratio    = min(TITLE_MAX_W / title_img.get_width(), 1.0)
        self.title_surf = pygame.transform.smoothscale(
            title_img,
            (
                int(title_img.get_width() * scale_ratio),
                int(title_img.get_height() * scale_ratio)
            )
        )
        self.title_rect = self.title_surf.get_rect(midtop=(WIDTH//2, TITLE_MARGIN_TOP))

        # Trash icon (closed/open) ----------------------------------------
        closed = pygame.image.load(PROJECT_ROOT / "assets" / "trash.svg").convert_alpha()
        opened = pygame.image.load(PROJECT_ROOT / "assets" / "trash_open.svg").convert_alpha()
        self.trash_closed = pygame.transform.smoothscale(closed, TRASH_SIZE)
        self.trash_open   = pygame.transform.smoothscale(opened, TRASH_SIZE)
        self.trash_rect   = pygame.Rect(
            TRASH_MARGIN,
            self.title_rect.bottom + 10,
            *TRASH_SIZE
        )

        # Drop-zone under title --------------------------------------------
        drop_top      = self.title_rect.bottom + 20
        avail_height  = HEIGHT - drop_top - SCROLL_AREA_HEIGHT
        self.drop_rect = pygame.Rect(
            (
                WIDTH//2 - DROP_SIZE[0]//2,
                drop_top + avail_height//2 - DROP_SIZE[1]//2
            ),
            DROP_SIZE
        )

        # Scrollable strip of game icons ----------------------------------
        self.scroll_rect = pygame.Rect(
            0, HEIGHT - SCROLL_AREA_HEIGHT,
            WIDTH, SCROLL_AREA_HEIGHT
        )
        self.icons: List[DraggableIcon] = []
        for idx, name in enumerate(registry.all_games()):
            sur = assets.get_icon(registry.cover_file(name), ICON_SIZE)
            self.icons.append(DraggableIcon(name, sur, idx))

        self.full_strip_width = ICON_SPACING + len(self.icons)*(ICON_SIZE[0] + ICON_SPACING)
        self.scroll_offset    = 0
        self._update_icon_positions()

        # Scrollbar drag state --------------------------------------------
        self.thumb_drag   = False
        self.thumb_offset = 0

        # Selection & controls ---------------------------------------------
        self.selected : List[str] = []
        self.snap_pos : Dict[str, Tuple[int,int]] = {}
        self.play_btn : Button|None = None
        self.mix_btn  : Button|None = None
        self.dropdown : Dropdown|None = None
        self._rebuild_buttons()

        # Drag state -------------------------------------------------------
        self.drag_icon           : DraggableIcon|None = None
        self.drag_from_selection = False

    # ───────────────────────────────────────────────────────── layout ─────
    def _max_offset(self) -> int:
        return max(0, self.full_strip_width - self.scroll_rect.width)

    def _update_icon_positions(self):
        y = (
            self.scroll_rect.y
            + (SCROLL_AREA_HEIGHT - ICON_SIZE[1] - SCROLLBAR_HEIGHT)//2
        )
        for icon in self.icons:
            x = ICON_SPACING + icon.index*(ICON_SIZE[0]+ICON_SPACING) - self.scroll_offset
            icon.rect.topleft = (x, y)

    def _track_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self.scroll_rect.x,
            self.scroll_rect.bottom - SCROLLBAR_HEIGHT,
            self.scroll_rect.width,
            SCROLLBAR_HEIGHT
        )

    def _thumb_rect(self) -> pygame.Rect:
        track = self._track_rect()
        m     = self._max_offset()
        if m == 0:
            return pygame.Rect(track)
        w = max(int(track.width*track.width/self.full_strip_width), 40)
        x = track.x + int(self.scroll_offset/m*(track.width - w))
        return pygame.Rect(x, track.y, w, track.height)

    def _scroll(self, dx: int):
        self.scroll_offset = min(max(self.scroll_offset + dx, 0), self._max_offset())
        self._update_icon_positions()

    def _scroll_to_ratio(self, r: float):
        self.scroll_offset = int(r * self._max_offset())
        self._update_icon_positions()

    def _snap_selected(self):
        cx, cy = self.drop_rect.center
        if len(self.selected) == 1:
            self.snap_pos = {
                self.selected[0]: (cx - ICON_SIZE[0]//2, cy - ICON_SIZE[1]//2)
            }
        elif len(self.selected) == 2:
            self.snap_pos = {
                self.selected[0]: (cx - ICON_SIZE[0] - 10, cy - ICON_SIZE[1]//2),
                self.selected[1]: (cx + 10,                cy - ICON_SIZE[1]//2),
            }

    def _rebuild_buttons(self):
        self.play_btn = self.mix_btn = None
        self.dropdown = None

        btn_y = self.drop_rect.centery - 20
        btn_x = self.drop_rect.right + 40

        if len(self.selected) == 1:
            # PLAY
            self.play_btn = Button(
                pygame.Rect(btn_x, btn_y, 150, 40),
                "PLAY",
                bg=BUTTON_BG_COLOR
            )
            # difficulty dropdown
            diffs = list(self.registry.difficulties(self.selected[0]).keys())
            if diffs:
                dr = pygame.Rect(
                    btn_x,
                    btn_y + 48,
                    150,
                    40
                )
                self.dropdown = Dropdown(dr, diffs, self.font)

        elif (
            len(self.selected) == 2
            and all(s.lower() not in COMBINED_NAMES for s in self.selected)
        ):
            # MIX
            self.mix_btn = Button(
                pygame.Rect(btn_x, btn_y, 150, 40),
                "MIX",
                bg=BUTTON_MIX_BG_COLOR
            )

    def _attempt_mix(self):
        key = tuple(sorted([s.lower() for s in self.selected]))
        if key in COMBOS:
            name, file = COMBOS[key]
        else:
            name, file = "Failed Mix", "fail.svg"
        if name not in self.registry.all_games():
            self.registry.register(name, file)
        self.selected = [name]
        self._snap_selected()
        self._rebuild_buttons()

    # ─────────────────────────────────────────────────────── event ─────
    def handle_event(self, ev: pygame.event.Event) -> tuple[str, Any] | None:
        # wheel scroll
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button in (4,5):
            if self.scroll_rect.collidepoint(ev.pos):
                self._scroll(-SCROLL_SPEED if ev.button==4 else SCROLL_SPEED)
                return None

        # dropdown
        if self.dropdown and self.dropdown.handle_event(ev):
            return None

        # start scrollbar thumb drag
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self._thumb_rect().collidepoint(ev.pos):
                self.thumb_drag   = True
                self.thumb_offset = ev.pos[0] - self._thumb_rect().x
                return None

            # click trash → clear
            if self.trash_rect.collidepoint(ev.pos) and not self.drag_icon:
                self.selected.clear()
                self.snap_pos.clear()
                self._rebuild_buttons()
                return None

            # drag from strip
            for icon in self.icons:
                if icon.rect.collidepoint(ev.pos):
                    icon.start_drag(ev.pos)
                    self.drag_icon = icon
                    return None

            # drag from selection
            for nm, pos in list(self.snap_pos.items()):
                if pygame.Rect(pos, ICON_SIZE).collidepoint(ev.pos):
                    surf = self.assets.get_icon(
                        self.registry.cover_file(nm), ICON_SIZE
                    )
                    tmp  = DraggableIcon(nm, surf, -1)
                    tmp.rect.topleft = pos
                    tmp.start_drag(ev.pos)
                    self.drag_icon = tmp
                    self.selected.remove(nm)
                    self._snap_selected()
                    self._rebuild_buttons()
                    return None

            # PLAY click
            if self.play_btn and self.play_btn.hovered(ev.pos):
                name = self.selected[0]
                params: dict[str,Any] = {}
                if self.dropdown:
                    params = self.registry.difficulties(name).get(self.dropdown.selected, {})
                return ("play", (name, params))

            # MIX click
            if self.mix_btn and self.mix_btn.hovered(ev.pos):
                self._attempt_mix()
                return ("mix", tuple(self.selected))

        # thumb move
        if ev.type == pygame.MOUSEMOTION and self.thumb_drag:
            track = self._track_rect()
            thumb = self._thumb_rect()
            new_x = min(
                max(ev.pos[0] - self.thumb_offset, track.x),
                track.right - thumb.width
            )
            ratio = (
                (new_x - track.x) / (track.width - thumb.width)
                if track.width > thumb.width else 0
            )
            self._scroll_to_ratio(ratio)
            return None

        # stop thumb
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.thumb_drag:
            self.thumb_drag = False
            return None

        # dragging icon
        if ev.type == pygame.MOUSEMOTION and self.drag_icon and self.drag_icon.dragging:
            self.drag_icon.drag(ev.pos)
            return None

        # drop icon
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1 and self.drag_icon:
            # into combo
            if self.drop_rect.colliderect(self.drag_icon.rect):
                nm = self.drag_icon.name
                if len(self.selected) < 2 and nm not in self.selected:
                    self.selected.append(nm)
                    self._snap_selected()
                    self._rebuild_buttons()
            # into trash
            if self.trash_rect.colliderect(self.drag_icon.rect):
                pass
            # reset drag
            self.drag_icon.stop_drag()
            self.drag_icon = None
            self._update_icon_positions()
            return None

        # arrow key scroll
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RIGHT:
                self._scroll(SCROLL_SPEED)
            elif ev.key == pygame.K_LEFT:
                self._scroll(-SCROLL_SPEED)

        return None

    # ───────────────────────────────────────────────────────── update ─────
    def update(self, dt: float) -> None:
        pass

    # ───────────────────────────────────────────────────────── draw ─────
    def draw(self) -> None:
        # background
        self.screen.fill(MENU_BG_COLOR)

        # title
        self.screen.blit(self.title_surf, self.title_rect)

        # trash
        tri = (
            self.trash_open
            if self.drag_icon and self.drag_icon.rect.colliderect(self.trash_rect)
            else self.trash_closed
        )
        self.screen.blit(tri, self.trash_rect)

        # combo border
        pygame.draw.rect(self.screen, DROP_BORDER_COLOR, self.drop_rect, width=3)

        # selected icons
        if len(self.selected) == 1:
            nm  = self.selected[0]
            big = self.assets.get_icon(
                self.registry.cover_file(nm),
                (ICON_SIZE[0]*2, ICON_SIZE[1]*2)
            )
            rect = big.get_rect(center=self.drop_rect.center)
            self.screen.blit(big, rect.topleft)
        else:
            for nm in self.selected:
                surf = self.assets.get_icon(
                    self.registry.cover_file(nm), ICON_SIZE
                )
                self.screen.blit(surf, self.snap_pos[nm])

        # scroll strip bg
        pygame.draw.rect(self.screen, SCROLL_BG_COLOR, self.scroll_rect)

        # strip icons
        for icon in self.icons:
            if icon.rect.right < 0 or icon.rect.left > WIDTH:
                continue
            icon.draw(self.screen)

        # dragging icon
        if self.drag_icon:
            self.drag_icon.draw(self.screen)

        # scrollbar
        pygame.draw.rect(self.screen, SCROLLBAR_TRACK_COLOR, self._track_rect())
        pygame.draw.rect(self.screen, SCROLLBAR_THUMB_COLOR, self._thumb_rect())

        # buttons & dropdown
        if self.play_btn:
            self.play_btn.draw(self.screen)
            if self.dropdown:
                self.dropdown.draw(self.screen)
        if self.mix_btn:
            self.mix_btn.draw(self.screen)
