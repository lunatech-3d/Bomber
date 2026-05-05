from __future__ import annotations

"""Admin helper for positioning bombsight label targets.

This tool opens the same bombsight image used by ``bombsite_kiosk.py`` and lets
an admin drag target labels into place. Press ``S`` to print updated target
coordinates that can be copied back into ``bombsite_kiosk.py``.
"""

import pygame

from bombsite_kiosk import (
    BOMBSIGHT_IMAGE_SCALE_BOOST,
    DESIGN_SIZE,
    PART_DEFS,
    PART_SIZE,
    TARGET_SLOTS,
    TITLE,
    AssetBank,
)

FPS = 60
PANEL_RECT = pygame.Rect(470, 130, 760, 520)
BG = (224, 219, 205)
TARGET_OUTLINE = (30, 120, 220)
TARGET_FILL = (238, 245, 255)
TEXT_COLOR = (25, 25, 25)


class LabelEditor:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont("arial", 24)
        self.small = pygame.font.SysFont("arial", 18)
        self.assets = AssetBank()
        self.dragging_index: int | None = None
        self.drag_offset = (0, 0)

        self.targets = [
            pygame.Rect(slot[0], slot[1], PART_SIZE[0], PART_SIZE[1]) for slot in TARGET_SLOTS
        ]

    def run(self) -> None:
        clock = pygame.time.Clock()
        running = True

        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_s:
                        self.print_targets()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.start_drag(event.pos)
                elif event.type == pygame.MOUSEMOTION and self.dragging_index is not None:
                    self.drag(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    self.dragging_index = None

            self.draw()
            pygame.display.flip()
            clock.tick(FPS)

    def start_drag(self, pos: tuple[int, int]) -> None:
        for i in range(len(self.targets) - 1, -1, -1):
            if self.targets[i].collidepoint(pos):
                self.dragging_index = i
                r = self.targets[i]
                self.drag_offset = (r.x - pos[0], r.y - pos[1])
                break

    def drag(self, pos: tuple[int, int]) -> None:
        idx = self.dragging_index
        if idx is None:
            return

        target = self.targets[idx]
        target.x = pos[0] + self.drag_offset[0]
        target.y = pos[1] + self.drag_offset[1]

    def draw(self) -> None:
        self.screen.fill(BG)
        self.screen.blit(self.font.render(f"{TITLE} • Label Target Editor", True, TEXT_COLOR), (40, 24))
        self.screen.blit(
            self.small.render("Drag labels. Press S to print TARGET_SLOTS. Esc to exit.", True, TEXT_COLOR),
            (40, 60),
        )

        self.draw_panel_image()

        for i, rect in enumerate(self.targets):
            pygame.draw.rect(self.screen, TARGET_FILL, rect, border_radius=8)
            pygame.draw.rect(self.screen, TARGET_OUTLINE, rect, 2, border_radius=8)
            name = PART_DEFS[i][0]
            label = self.small.render(name, True, TARGET_OUTLINE)
            self.screen.blit(label, (rect.x + 7, rect.y + 14))

    def draw_panel_image(self) -> None:
        pygame.draw.rect(self.screen, (186, 176, 155), PANEL_RECT, border_radius=20)
        pygame.draw.rect(self.screen, (95, 87, 71), PANEL_RECT, 3, border_radius=20)

        if not self.assets.bombsight_photo:
            return

        img = self.assets.bombsight_photo
        scale = min(PANEL_RECT.width / img.get_width(), PANEL_RECT.height / img.get_height())
        scale *= BOMBSIGHT_IMAGE_SCALE_BOOST
        new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
        scaled = pygame.transform.smoothscale(img, new_size)
        self.screen.blit(scaled, scaled.get_rect(center=PANEL_RECT.center).topleft)

    def print_targets(self) -> None:
        coords = [(r.x, r.y) for r in self.targets]
        print("\n# Copy this into bombsite_kiosk.py")
        print(f"TARGET_SLOTS = {coords}")


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode(DESIGN_SIZE)
    pygame.display.set_caption("Bombsight Label Target Editor")
    LabelEditor(screen).run()
    pygame.quit()


if __name__ == "__main__":
    main()