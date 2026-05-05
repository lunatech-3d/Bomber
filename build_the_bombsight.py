"""Build the Bombsight - museum kiosk prototype.

Standalone Pygame kiosk app with:
- Full-screen window (mouse + touch support)
- Drag-to-assemble bombsight activity with snap+lock parts
- Unlockable targeting mini-game with moving map background

Designed for easy image-asset replacement later.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random
import sys
import pygame

# ---------------------------- Configuration ---------------------------- #
TITLE = "Build the Bombsight"
DESIGN_SIZE = (1280, 720)
FPS = 60
ASSET_DIR = Path(__file__).parent / "assets"

PART_DEFS = [
    ("Stabilizer", (239, 196, 76)),
    ("Drift Knob", (82, 190, 128)),
    ("Optics", (93, 173, 226)),
    ("Altitude Dial", (236, 112, 99)),
    ("Release Link", (165, 105, 189)),
]


@dataclass
class Part:
    name: str
    color: tuple[int, int, int]
    rect: pygame.Rect
    target: pygame.Rect
    home: tuple[int, int]
    locked: bool = False

    def reset(self) -> None:
        self.rect.topleft = self.home
        self.locked = False


class AssetBank:
    """Optional image hooks; app falls back to simple shapes if files don't exist."""

    def __init__(self) -> None:
        self.panel = self._load("bombsight_panel.png")
        self.map_bg = self._load("map_bg.png")

    def _load(self, filename: str) -> pygame.Surface | None:
        path = ASSET_DIR / filename
        if path.exists():
            return pygame.image.load(path.as_posix()).convert_alpha()
        return None


class AssemblyScene:
    def __init__(self, screen_rect: pygame.Rect, fonts: dict[str, pygame.font.Font]) -> None:
        self.screen_rect = screen_rect
        self.fonts = fonts
        self.dragging: Part | None = None
        self.drag_offset = (0, 0)
        self.parts = self._build_parts()

    def _build_parts(self) -> list[Part]:
        parts = []
        sx, sy = 40, 170
        for i, (name, color) in enumerate(PART_DEFS):
            r = pygame.Rect(sx, sy + i * 90, 220, 62)
            t = pygame.Rect(520 + (i % 2) * 260, 190 + (i // 2) * 130, 220, 62)
            parts.append(Part(name=name, color=color, rect=r.copy(), target=t, home=r.topleft))
        return parts

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for part in reversed(self.parts):
                if not part.locked and part.rect.collidepoint(event.pos):
                    self.dragging = part
                    self.drag_offset = (part.rect.x - event.pos[0], part.rect.y - event.pos[1])
                    break

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.dragging.rect.x = event.pos[0] + self.drag_offset[0]
            self.dragging.rect.y = event.pos[1] + self.drag_offset[1]

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            part = self.dragging
            self.dragging = None
            if part.rect.colliderect(part.target.inflate(24, 24)):
                part.rect.topleft = part.target.topleft
                part.locked = True
            else:
                part.rect.topleft = part.home

    def completed(self) -> bool:
        return all(p.locked for p in self.parts)

    def draw(self, screen: pygame.Surface, assets: AssetBank) -> None:
        screen.fill((224, 219, 205))
        screen.blit(self.fonts["title"].render(TITLE, True, (30, 30, 30)), (40, 30))
        screen.blit(
            self.fonts["small"].render(
                "Norden-style training rig • Burroughs Corporation, Plymouth, Michigan", True, (55, 55, 55)
            ),
            (42, 94),
        )
        screen.blit(self.fonts["body"].render("Drag each part to its matching location.", True, (42, 42, 42)), (40, 660))

        panel_rect = pygame.Rect(470, 130, 760, 520)
        if assets.panel:
            screen.blit(pygame.transform.smoothscale(assets.panel, panel_rect.size), panel_rect.topleft)
        else:
            pygame.draw.rect(screen, (186, 176, 155), panel_rect, border_radius=20)
            pygame.draw.rect(screen, (95, 87, 71), panel_rect, 3, border_radius=20)

        for part in self.parts:
            pygame.draw.rect(screen, (110, 110, 110), part.target, 2, border_radius=10)
            if not part.locked:
                hint = self.fonts["small"].render(part.name, True, (92, 92, 92))
                screen.blit(hint, (part.target.x + 8, part.target.y + 18))

        for part in self.parts:
            self._draw_part(screen, part, transparent=(part is self.dragging and not part.locked))

    def _draw_part(self, screen: pygame.Surface, part: Part, transparent: bool = False) -> None:
        alpha = 180 if transparent else 255
        surf = pygame.Surface(part.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(surf, (*part.color, alpha), surf.get_rect(), border_radius=9)
        pygame.draw.rect(surf, (30, 30, 30, alpha), surf.get_rect(), 2, border_radius=9)
        label = self.fonts["small"].render(part.name, True, (20, 20, 20))
        surf.blit(label, label.get_rect(center=surf.get_rect().center))
        screen.blit(surf, part.rect.topleft)


class TargetingScene:
    def __init__(self, screen_rect: pygame.Rect, fonts: dict[str, pygame.font.Font]) -> None:
        self.rect = screen_rect
        self.fonts = fonts
        self.crosshair = [screen_rect.centerx, screen_rect.centery]
        self.plane = [screen_rect.centerx, 130]
        self.targets = [self._new_target() for _ in range(4)]
        self.radius = 30
        self.score = 0
        self.scroll = 0
        self.scroll_speed = 1
        self.seconds_total = 60
        self.start_ms = pygame.time.get_ticks()
        self.game_over = False

    def _new_target(self) -> list[int]:
        return [random.randint(240, self.rect.width - 240), random.randint(190, self.rect.height - 100)]

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.reset()
            return
        if self.game_over:
            return

        if event.type == pygame.MOUSEMOTION:
            self.crosshair[0], self.crosshair[1] = event.pos
        elif event.type == pygame.FINGERMOTION:
            self.crosshair[0] = int(event.x * self.rect.width)
            self.crosshair[1] = int(event.y * self.rect.height)
        elif event.type == pygame.FINGERDOWN:
            self.crosshair[0] = int(event.x * self.rect.width)
            self.crosshair[1] = int(event.y * self.rect.height)
            self._shoot()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._shoot()

    def _shoot(self) -> None:
        for i, target in enumerate(self.targets):
            dx = self.crosshair[0] - target[0]
            dy = self.crosshair[1] - target[1]
            if dx * dx + dy * dy <= self.radius * self.radius:
                self.score += 1
                self.targets[i] = self._new_target()
                break

    def update(self) -> None:
        now = pygame.time.get_ticks()
        if now - self.start_ms >= self.seconds_total * 1000:
            self.game_over = True
            return

        self.scroll = (self.scroll + self.scroll_speed) % 120
        keys = pygame.key.get_pressed()
        move_speed = 5
        if keys[pygame.K_LEFT]:
            self.plane[0] -= move_speed
        if keys[pygame.K_RIGHT]:
            self.plane[0] += move_speed
        if keys[pygame.K_UP]:
            self.plane[1] -= move_speed
        if keys[pygame.K_DOWN]:
            self.plane[1] += move_speed
        self.plane[0] = max(30, min(self.rect.width - 30, self.plane[0]))
        self.plane[1] = max(90, min(self.rect.height - 60, self.plane[1]))
        self.crosshair[0], self.crosshair[1] = self.plane[0], self.plane[1] + 120

    def reset(self) -> None:
        self.plane = [self.rect.centerx, 130]
        self.targets = [self._new_target() for _ in range(4)]
        self.score = 0
        self.scroll = 0
        self.start_ms = pygame.time.get_ticks()
        self.game_over = False

    def draw(self, screen: pygame.Surface, assets: AssetBank) -> None:
        screen.fill((19, 34, 56))
        self._draw_background(screen, assets)
        screen.blit(self.fonts["title"].render("Targeting Drill", True, (240, 240, 240)), (40, 26))
        screen.blit(self.fonts["small"].render("Arrow keys fly plane • click/tap to drop bombs • R to restart.", True, (225, 225, 225)), (42, 92))
        screen.blit(self.fonts["body"].render(f"Score: {self.score}", True, (255, 242, 130)), (1090, 45))
        seconds_left = max(0, self.seconds_total - (pygame.time.get_ticks() - self.start_ms) // 1000)
        screen.blit(self.fonts["body"].render(f"Time: {seconds_left}s", True, (255, 242, 130)), (900, 88))

        for target in self.targets:
            pygame.draw.circle(screen, (255, 88, 88), target, self.radius)
            pygame.draw.circle(screen, (255, 255, 255), target, self.radius, 3)
        self._draw_plane(screen)
        self._draw_crosshair(screen)
        if self.game_over:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 140))
            screen.blit(overlay, (0, 0))
            msg = self.fonts["title"].render("Mission Complete", True, (255, 255, 255))
            hint = self.fonts["body"].render("Press R to try again", True, (245, 245, 245))
            screen.blit(msg, msg.get_rect(center=(self.rect.centerx, self.rect.centery - 20)))
            screen.blit(hint, hint.get_rect(center=(self.rect.centerx, self.rect.centery + 45)))

    def _draw_background(self, screen: pygame.Surface, assets: AssetBank) -> None:
        if assets.map_bg:
            img = pygame.transform.smoothscale(assets.map_bg, (self.rect.width, self.rect.height))
            for x in (-self.scroll, self.rect.width - self.scroll):
                screen.blit(img, (x, 0))
            return

        colors = [(36, 61, 92), (42, 74, 114), (49, 88, 135)]
        for i, c in enumerate(colors):
            y = 150 + i * 170
            offset = (self.scroll * (i + 1)) % 180
            for x in range(-180, self.rect.width + 180, 180):
                pygame.draw.rect(screen, c, (x - offset, y, 150, 120), border_radius=12)

    def _draw_crosshair(self, screen: pygame.Surface) -> None:
        x, y = self.crosshair
        pygame.draw.circle(screen, (255, 255, 255), (x, y), 24, 2)
        pygame.draw.line(screen, (255, 255, 255), (x - 42, y), (x + 42, y), 2)
        pygame.draw.line(screen, (255, 255, 255), (x, y - 42), (x, y + 42), 2)

    def _draw_plane(self, screen: pygame.Surface) -> None:
        x, y = self.plane
        pygame.draw.polygon(screen, (235, 235, 235), [(x, y - 20), (x - 22, y + 16), (x + 22, y + 16)])
        pygame.draw.rect(screen, (200, 200, 200), (x - 34, y + 6, 68, 8), border_radius=4)


class KioskApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.fonts = {
            "title": pygame.font.SysFont("arial", 54, bold=True),
            "body": pygame.font.SysFont("arial", 30),
            "small": pygame.font.SysFont("arial", 22),
        }
        self.assets = AssetBank()
        self.assembly = AssemblyScene(self.screen.get_rect(), self.fonts)
        self.targeting = TargetingScene(self.screen.get_rect(), self.fonts)
        self.scene = "assembly"

    def run(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.quit()
                if self.scene == "assembly":
                    self.assembly.handle_event(event)
                else:
                    self.targeting.handle_event(event)

            if self.scene == "assembly" and self.assembly.completed():
                self.scene = "targeting"
            if self.scene == "targeting":
                self.targeting.update()

            if self.scene == "assembly":
                self.assembly.draw(self.screen, self.assets)
            else:
                self.targeting.draw(self.screen, self.assets)

            pygame.display.flip()
            self.clock.tick(FPS)

    @staticmethod
    def quit() -> None:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    KioskApp().run()
