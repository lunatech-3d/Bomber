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
BOMBSIGHT_IMAGE = Path(r"c:\bomber\football.jpg")

PART_DEFS = [
    ("Leveling Knob", (239, 196, 76), "Levels the bombsight so calculations stay accurate in flight."),
    ("Turn & Drift Knob", (82, 190, 128), "Compensates for wind drift and aircraft turn effects."),
    ("Rate & Displacement Knob", (93, 173, 226), "Adjusts target movement rate and displacement corrections."),
    ("Disc Speed Drum", (236, 112, 99), "Sets bombing disc speed values used by the aiming mechanism."),
    ("Eye Piece", (165, 105, 189), "Viewing lens used to align and track the target area."),
]

PART_SIZE = (165, 46)
PART_BG_COLOR = (40, 110, 220)
PART_BORDER_COLOR = (192, 192, 192)
PART_TEXT_COLOR = (255, 255, 255)
BOMBSIGHT_IMAGE_SCALE_BOOST = 1.15

HOME_START = (40, 170)
HOME_Y_STEP = 90
TARGET_SLOTS = [(488, 490), (1014, 632), (1049, 390), (998, 556), (816, 121)]
TARGET_LINES = [((801, 306), (836, 156)), ((1032, 659), (928, 631)), ((1015, 583), (928, 529)), ((1066, 425), (994, 512)), ((543, 403), (507, 501))]

RETURN_LERP_SPEED = 0.18
RETURN_SNAP_DISTANCE = 1.5


@dataclass
class Part:
    name: str
    color: tuple[int, int, int]
    rect: pygame.Rect
    target: pygame.Rect
    home: tuple[int, int]
    definition: str
    locked: bool = False
    returning: bool = False
    return_pos: tuple[float, float] | None = None

    def reset(self) -> None:
        self.rect.topleft = self.home
        self.locked = False
        self.returning = False
        self.return_pos = None


class AssetBank:
    """Optional image hooks; app falls back to simple shapes if files don't exist."""

    def __init__(self) -> None:
        self.panel = self._load_asset("bombsight_panel.png")
        self.map_bg = self._load_asset("map_bg.png")
        self.bombsight_photo = self._load_absolute(BOMBSIGHT_IMAGE)

    def _load_asset(self, filename: str) -> pygame.Surface | None:
        path = ASSET_DIR / filename
        if path.exists():
            return pygame.image.load(path.as_posix()).convert_alpha()
        return None

    def _load_absolute(self, path: Path) -> pygame.Surface | None:
        if path.exists():
            return pygame.image.load(path.as_posix()).convert()
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
        sx, sy = HOME_START        
        part_width, part_height = PART_SIZE

        self.start_button = pygame.Rect(980, 650, 250, 48)
        self.show_start_button = False
        self.current_definition = "Place a label on the correct slot to see its definition."
        for i, (name, color, definition) in enumerate(PART_DEFS):
            r = pygame.Rect(sx, sy + i * HOME_Y_STEP, part_width, part_height)
            target_x, target_y = TARGET_SLOTS[i]
            t = pygame.Rect(target_x, target_y, part_width, part_height)
            parts.append(Part(name=name, color=color, rect=r.copy(), target=t, home=r.topleft, definition=definition))

        return parts

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for part in reversed(self.parts):
                if not part.locked and part.rect.collidepoint(event.pos):
                    self.dragging = part
                    part.returning = False
                    part.return_pos = (float(part.rect.x), float(part.rect.y))
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
                self.current_definition = part.definition
                part.returning = False
                part.return_pos = None
            else:
                part.returning = True
                part.return_pos = (float(part.rect.x), float(part.rect.y))

    def update(self) -> None:
        for part in self.parts:
            if not part.returning or part.locked:
                continue

            if part.return_pos is None:
                part.return_pos = (float(part.rect.x), float(part.rect.y))

            x, y = part.return_pos
            hx, hy = part.home

            x += (hx - x) * RETURN_LERP_SPEED
            y += (hy - y) * RETURN_LERP_SPEED

            if abs(hx - x) <= RETURN_SNAP_DISTANCE and abs(hy - y) <= RETURN_SNAP_DISTANCE:
                x, y = float(hx), float(hy)
                part.returning = False
                part.return_pos = None
            else:
                part.return_pos = (x, y)

            part.rect.topleft = (round(x), round(y))

    def completed(self) -> bool:
        return all(p.locked for p in self.parts)

    def ready_to_start(self) -> bool:
        return self.completed()

    def handle_start_click(self, pos: tuple[int, int]) -> bool:
        return self.ready_to_start() and self.start_button.collidepoint(pos)

    def draw(self, screen: pygame.Surface, assets: AssetBank) -> None:
        screen.fill((224, 219, 205))

        screen.blit(self.fonts["title"].render(TITLE, True, (30, 30, 30)), (40, 30))
        screen.blit(
            self.fonts["small"].render(
                "Burroughs Corporation - Norden Bombsight Training Simulator",
                True,
                (55, 55, 55),
            ),
            (42, 94),
        )
        screen.blit(
            self.fonts["body"].render(
                "Drag each part to its matching location.",
                True,
                (42, 42, 42),
            ),
            (40, 610),
        )

        panel_rect = pygame.Rect(470, 130, 760, 520)

        if assets.bombsight_photo:
            pygame.draw.rect(screen, (186, 176, 155), panel_rect, border_radius=20)
            pygame.draw.rect(screen, (95, 87, 71), panel_rect, 3, border_radius=20)

            img = assets.bombsight_photo
            scale = min(panel_rect.width / img.get_width(), panel_rect.height / img.get_height())
            scale *= BOMBSIGHT_IMAGE_SCALE_BOOST
            new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
            scaled = pygame.transform.smoothscale(img, new_size)

            img_rect = scaled.get_rect(center=panel_rect.center)
            image_clip = panel_rect.inflate(-8, -8)
            previous_clip = screen.get_clip()
            screen.set_clip(image_clip)
            screen.blit(scaled, img_rect.topleft)
            screen.set_clip(previous_clip)

        elif assets.panel:
            screen.blit(pygame.transform.smoothscale(assets.panel, panel_rect.size), panel_rect.topleft)

        else:
            pygame.draw.rect(screen, (186, 176, 155), panel_rect, border_radius=20)
            pygame.draw.rect(screen, (95, 87, 71), panel_rect, 3, border_radius=20)

        for i, part in enumerate(self.parts):
            if i < len(TARGET_LINES):
                pygame.draw.line(screen, (72, 72, 72), TARGET_LINES[i][0], TARGET_LINES[i][1], 3)
            pygame.draw.rect(screen, (110, 110, 110), part.target, 2, border_radius=10)
        self._draw_definition_box(screen)
        self.show_start_button = self.completed()
        if self.show_start_button:
            pygame.draw.rect(screen, (40, 130, 75), self.start_button, border_radius=8)
            pygame.draw.rect(screen, (230, 230, 230), self.start_button, 2, border_radius=8)
            txt = self.fonts["small"].render("Start Simulation", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=self.start_button.center))

        mouse = pygame.mouse.get_pos()
        for part in self.parts:
            if part.locked and part.target.collidepoint(mouse):
                self.current_definition = part.definition

        for part in self.parts:
            self._draw_part(screen, part, transparent=(part is self.dragging and not part.locked))

    def _draw_part(self, screen: pygame.Surface, part: Part, transparent: bool = False) -> None:
        alpha = 180 if transparent else 255
        surf = pygame.Surface(part.rect.size, pygame.SRCALPHA)

        pygame.draw.rect(surf, (*PART_BG_COLOR, alpha), surf.get_rect(), border_radius=9)
        pygame.draw.rect(surf, (*PART_BORDER_COLOR, alpha), surf.get_rect(), 2, border_radius=9)

        label = self.fonts["small"].render(part.name, True, PART_TEXT_COLOR)
        surf.blit(label, label.get_rect(center=surf.get_rect().center))

        screen.blit(surf, part.rect.topleft)

    def _draw_definition_box(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(40, 645, 920, 64)
        pygame.draw.rect(screen, (246, 241, 226), rect, border_radius=10)
        pygame.draw.rect(screen, (95, 87, 71), rect, 2, border_radius=10)
        label = self.fonts["small"].render(self.current_definition, True, (30, 30, 30))
        screen.blit(label, (rect.x + 12, rect.y + 20))


class TargetingScene:
    def __init__(self, screen_rect: pygame.Rect, fonts: dict[str, pygame.font.Font]) -> None:
        self.rect = screen_rect
        self.fonts = fonts
        self.crosshair = [screen_rect.centerx, screen_rect.centery]
        self.target = [random.randint(240, 1040), random.randint(190, 620)]
        self.radius = 30
        self.score = 0
        self.scroll = 0

    def handle_event(self, event: pygame.event.Event) -> None:
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
        dx = self.crosshair[0] - self.target[0]
        dy = self.crosshair[1] - self.target[1]

        if dx * dx + dy * dy <= self.radius * self.radius:
            self.score += 1
            self.target = [random.randint(240, 1040), random.randint(190, 620)]

    def update(self) -> None:
        self.scroll = (self.scroll + 2) % 120

    def draw(self, screen: pygame.Surface, assets: AssetBank) -> None:
        screen.fill((19, 34, 56))
        self._draw_background(screen, assets)

        screen.blit(self.fonts["title"].render("Targeting Drill", True, (240, 240, 240)), (40, 26))
        screen.blit(
            self.fonts["small"].render(
                "Track the map, center target, tap/click to lock hit.",
                True,
                (225, 225, 225),
            ),
            (42, 92),
        )
        screen.blit(self.fonts["body"].render(f"Score: {self.score}", True, (255, 242, 130)), (1090, 45))

        pygame.draw.circle(screen, (255, 88, 88), self.target, self.radius)
        pygame.draw.circle(screen, (255, 255, 255), self.target, self.radius, 3)

        self._draw_crosshair(screen)

    def _draw_background(self, screen: pygame.Surface, assets: AssetBank) -> None:
        if assets.map_bg:
            img = pygame.transform.smoothscale(assets.map_bg, (self.rect.width, self.rect.height))
            for x in (-self.scroll, self.rect.width - self.scroll):
                screen.blit(img, (x, 0))
            return

        colors = [(36, 61, 92), (42, 74, 114), (49, 88, 135)]

        for i, color in enumerate(colors):
            y = 150 + i * 170
            offset = (self.scroll * (i + 1)) % 180

            for x in range(-180, self.rect.width + 180, 180):
                pygame.draw.rect(screen, color, (x - offset, y, 150, 120), border_radius=12)

    def _draw_crosshair(self, screen: pygame.Surface) -> None:
        x, y = self.crosshair

        pygame.draw.circle(screen, (255, 255, 255), (x, y), 24, 2)
        pygame.draw.line(screen, (255, 255, 255), (x - 42, y), (x + 42, y), 2)
        pygame.draw.line(screen, (255, 255, 255), (x, y - 42), (x, y + 42), 2)


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
                    if (
                        event.type == pygame.MOUSEBUTTONDOWN
                        and event.button == 1
                        and self.assembly.handle_start_click(event.pos)
                    ):
                        self.scene = "targeting"
                else:
                    self.targeting.handle_event(event)

            if self.scene == "assembly":
                self.assembly.update()

            elif self.scene == "targeting":
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
