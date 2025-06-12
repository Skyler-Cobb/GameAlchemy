"""
main.py

Entry point.  Builds registry via auto-discovery, launches menu, and
runs a generic loop that swaps into any Scene returned by registry.launch_game.
"""

import sys
import pygame

from config              import WIDTH, HEIGHT, FPS, GAMES, COVERS_DIR
from core.asset_manager  import AssetManager
from core.game_registry  import GameRegistry
from scenes.loader       import register_all
from ui.menu             import MenuUI

def build_registry() -> GameRegistry:
    reg = GameRegistry()
    # 1) register all covers (placeholders for combos & unimplemented games)
    for name, cover in GAMES:
        reg.register(name, cover)
    # 2) auto-discover & register any scenes with register(registry)
    register_all(reg)
    return reg

def main() -> None:
    pygame.init()
    pygame.display.set_caption("GameAlchemy")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock  = pygame.time.Clock()

    registry = build_registry()
    assets   = AssetManager(COVERS_DIR)

    menu    = MenuUI(screen, registry, assets)
    current = menu

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
                break

            # dispatch to current scene/menu
            result = current.handle_event(ev)

            # ▶️ Menu PLAY/MIX
            if isinstance(current, MenuUI) and isinstance(result, tuple):
                cmd, payload = result
                if cmd == "play":
                    name, params = payload
                    scene = registry.launch_game(name, screen, **params)
                    if scene:
                        current = scene
                elif cmd == "mix":
                    # mixing is internal to MenuUI
                    pass
                continue

            # 🔄 Game scene → back to menu
            if not isinstance(current, MenuUI) and result == "menu":
                current = menu
                continue

        current.update(dt)
        current.draw()
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
