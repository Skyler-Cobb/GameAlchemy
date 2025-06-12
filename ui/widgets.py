"""
Reusable UI widgets (buttons & draggable icons/games).
"""
from __future__ import annotations
import pygame
from typing import Tuple
from config    import ICON_SIZE, FONT_NAME
from constants import (BUTTON_BG_COLOR, BUTTON_MIX_BG_COLOR,
                       BUTTON_FG_COLOR)

# --------------------------------------------------------------------
class Button:
    def __init__(self, rect: pygame.Rect, text: str,
                 bg=BUTTON_BG_COLOR, fg=BUTTON_FG_COLOR):
        self.rect = rect
        self.text = text
        self.bg   = bg
        self.fg   = fg

        font = pygame.font.Font(FONT_NAME, 20)
        self.surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        self.surface.fill(bg)
        lbl = font.render(text, True, fg)
        self.surface.blit(lbl, lbl.get_rect(center=self.surface.get_rect().center))

    def draw(self, screen):  screen.blit(self.surface, self.rect.topleft)
    def hovered(self, pos):  return self.rect.collidepoint(pos)

# --------------------------------------------------------------------
class DraggableIcon:
    def __init__(self, name: str, surface: pygame.Surface, index: int):
        self.name    = name
        self.surface = surface
        self.index   = index            # order inside scrolling strip
        self.rect    = pygame.Rect(0, 0, *ICON_SIZE)

        self.dragging = False
        self._offset  = (0, 0)

    # -------------------------------------------------------------- #
    def start_drag(self, mouse_pos):
        mx,my = mouse_pos
        ox,oy = self.rect.topleft
        self._offset = (mx-ox, my-oy)
        self.dragging = True

    def drag(self, mouse_pos):
        mx,my = mouse_pos
        ox,oy = self._offset
        self.rect.topleft = (mx-ox, my-oy)

    def stop_drag(self):
        self.dragging = False

    def draw(self, screen):
        screen.blit(self.surface, self.rect.topleft)

class Dropdown:
    """
    A simple dropdown: click to open/close, click an option to select it.
    """
    def __init__(
        self,
        rect: pygame.Rect,
        options: list[str],
        font: pygame.font.Font,
        bg=(60,60,60),
        fg=(220,220,220),
        highlight=(100,100,100),
    ):
        self.rect      = rect
        self.options   = options
        self.font      = font
        self.bg        = bg
        self.fg        = fg
        self.hl       = highlight
        self.open      = False
        self.selected  = options[0] if options else ""
        # pre-render labels
        self._labels = [self.font.render(opt, True, fg) for opt in options]

    def handle_event(self, event):
        if not self.options:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.open:
                # check each option
                for idx, opt in enumerate(self.options):
                    opt_rect = pygame.Rect(
                        self.rect.x,
                        self.rect.y + (idx+1)*self.rect.height,
                        self.rect.width,
                        self.rect.height,
                    )
                    if opt_rect.collidepoint(event.pos):
                        self.selected = opt
                        self.open = False
                        return True
                # clicked outside options: close
                if not self.rect.collidepoint(event.pos):
                    self.open = False
                    return False
            else:
                if self.rect.collidepoint(event.pos):
                    self.open = True
                    return True
        return False

    def draw(self, screen):
        # draw current
        pygame.draw.rect(screen, self.bg, self.rect)
        lbl = self.font.render(self.selected, True, self.fg)
        screen.blit(lbl, lbl.get_rect(center=self.rect.center))
        # draw arrow
        pygame.draw.polygon(
            screen,
            self.fg,
            [
                (self.rect.right - 12, self.rect.centery - 4),
                (self.rect.right - 4, self.rect.centery - 4),
                (self.rect.right - 8, self.rect.centery + 4),
            ],
        )
        # draw options if open
        if self.open:
            for idx, label in enumerate(self._labels):
                opt_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y + (idx+1)*self.rect.height,
                    self.rect.width,
                    self.rect.height,
                )
                # use the string in self.options, not label.get_text()
                bg_color = self.hl if self.options[idx] == self.selected else self.bg
                pygame.draw.rect(screen, bg_color, opt_rect)
                screen.blit(label, label.get_rect(center=opt_rect.center))