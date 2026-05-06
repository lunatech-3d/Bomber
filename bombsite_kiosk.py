from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import math
import random
import sys
import pygame

# ---------------------------- Configuration ---------------------------- #
TITLE = "Build the Bombsight"
FPS = 60
ASSET_DIR = Path(__file__).parent / "assets"
BOMBSIGHT_IMAGE = Path(r"c:\bomber\football.jpg")

PART_DEFS = [
    ("Leveling Knob", (239, 196, 76), "Levels the bombsight so calculations stay accurate in flight."),
    ("Turn & Drift Knob", (82, 190, 128), "Compensates for wind drift and aircraft turn effects."),
    ("Rate & Displ.Knob", (93, 173, 226), "Adjusts target movement rate and displacement corrections."),
    ("Disc Speed Drum", (236, 112, 99), "Sets bombing disc speed values used by the aiming mechanism."),
    ("Eye Piece", (165, 105, 189), "Viewing lens used to align and track the target area."),
]

PART_SIZE = (165, 46)
PART_BG_COLOR = (255, 255, 255)
PART_BORDER_COLOR = (255, 255, 255)
PART_TEXT_COLOR = (30, 30, 30)
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
    """Existing drag-and-drop assembly scene (unchanged gameplay)."""

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

        self.start_button = pygame.Rect(980, 714, 250, 48)
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

    def handle_start_click(self, pos: tuple[int, int]) -> bool:
        return self.completed() and self.start_button.collidepoint(pos)

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

        self._draw_definition_box(screen)
        if self.completed():
            pygame.draw.rect(screen, (40, 130, 75), self.start_button, border_radius=8)
            pygame.draw.rect(screen, (230, 230, 230), self.start_button, 2, border_radius=8)
            txt = self.fonts["small"].render("Start Bomb Run", True, (255, 255, 255))
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

        label = self.fonts["small"].render(part.name, True, PART_TEXT_COLOR)
        surf.blit(label, label.get_rect(center=surf.get_rect().center))

        screen.blit(surf, part.rect.topleft)

    def _draw_definition_box(self, screen: pygame.Surface) -> None:
        rect = pygame.Rect(40, 640, 920, 64)
        pygame.draw.rect(screen, (246, 241, 226), rect, border_radius=10)
        pygame.draw.rect(screen, (95, 87, 71), rect, 2, border_radius=10)
        label = self.fonts["small"].render(self.current_definition, True, (30, 30, 30))
        screen.blit(label, (rect.x + 12, rect.y + 20))


class BombRunScene:
    """Keyboard-driven bombsight simulation with drift correction and timed bomb release."""

    def __init__(self, screen_rect: pygame.Rect, fonts: dict[str, pygame.font.Font]) -> None:
        self.rect = screen_rect
        self.fonts = fonts
        self.viewport_radius = min(screen_rect.width, screen_rect.height) // 3
        self.viewport_center = (screen_rect.centerx, screen_rect.centery + 20)
        self.reset()

    def reset(self) -> None:
        # Environmental errors to correct.
        self.wind_push = random.uniform(-1.2, 1.2)
        self.forward_speed = random.uniform(0.70, 0.95)

        # User adjustments (heading and speed controls).
        self.heading_correction = 0.0
        self.speed_adjust = 0.0
        self.min_speed = 0.25
        self.max_speed = 2.2

        self.run_time = 0.0
        self.max_run_time = 60.0
        self.ideal_release_y = -26.0

        self.targets = [self._new_target() for _ in range(4)]
        self.total_drops = 0
        self.successful_hits = 0
        self.result_ready = False
        self.impact_distance = 0.0
        self.rating = ""
        self.impact_effects: list[dict[str, float | str]] = []

    def _new_target(self) -> dict[str, float]:
        return {"x": random.uniform(-160, 160), "y": random.uniform(220, 560)}

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and not self.result_ready:
            if event.key == pygame.K_LEFT:
                self.heading_correction -= 0.16
            elif event.key == pygame.K_RIGHT:
                self.heading_correction += 0.16
            elif event.key == pygame.K_UP:
                self.speed_adjust += 0.10
            elif event.key == pygame.K_DOWN:
                self.speed_adjust -= 0.10
            elif event.key == pygame.K_SPACE:
                self._release_bomb()
        return self.result_ready

    def _release_bomb(self) -> None:
        self.total_drops += 1
        closest = None
        for i, target in enumerate(self.targets):
            timing_error = abs(target["y"] - self.ideal_release_y)
            lateral_error = abs(target["x"])
            control_error = abs(self.wind_push - self.heading_correction) * 65 + abs(self.current_speed() - 1.15) * 55
            distance = math.hypot(lateral_error * 0.9 + control_error * 0.25, timing_error * 0.95)
            if closest is None or distance < closest[1]:
                closest = (i, distance)

        if closest is None:
            return

        index, self.impact_distance = closest
        impact_target = self.targets[index]
        timing_offset = impact_target["y"] - self.ideal_release_y
        lateral_offset = impact_target["x"]
        impact_x = max(-self.viewport_radius + 18, min(self.viewport_radius - 18, lateral_offset * 0.75 + (self.wind_push - self.heading_correction) * 55))
        impact_y = max(-self.viewport_radius + 18, min(self.viewport_radius - 18, timing_offset * 0.35))
        if self.impact_distance <= 42:
            self.rating = "Direct Hit"
            self.successful_hits += 1
            self.impact_effects.append(
                {"kind": "blast", "x": 0.0, "y": 0.0, "age": 0.0, "duration": 0.55, "radius": 14.0}
            )
            # Remove hit target from view immediately; recycle below the viewport.
            self.targets[index] = {"x": random.uniform(-160, 160), "y": random.uniform(620, 820)}
        elif self.impact_distance <= 130:
            self.rating = "Near Miss"
            self.impact_effects.append(
                {"kind": "crater", "x": impact_x, "y": impact_y, "age": 0.0, "duration": 2.2, "radius": 10.0}
            )
        else:
            self.rating = "Miss"
            self.impact_effects.append(
                {"kind": "crater", "x": impact_x, "y": impact_y, "age": 0.0, "duration": 2.2, "radius": 10.0}
            )

    def update(self, dt: float) -> None:
        if self.result_ready:
            return

        self.run_time = min(self.max_run_time, self.run_time + dt)
        speed = self.current_speed()

        if speed <= self.min_speed:
            self.rating = "Stalled Aircraft"
            self.result_ready = True
            return

        for target in self.targets:
            target["x"] += (self.wind_push - self.heading_correction) * 55 * dt
            target["y"] -= speed * 62 * dt
            radial_distance = math.hypot(target["x"], target["y"])
            if radial_distance > self.viewport_radius + 36 and target["y"] < 0:
                target.update(self._new_target())
                target["y"] = random.uniform(420, 620)
            target["x"] = max(-260, min(260, target["x"]))

        for effect in self.impact_effects:
            effect["age"] += dt
            effect["y"] -= speed * 62 * dt
        self.impact_effects = [effect for effect in self.impact_effects if effect["age"] < effect["duration"]]
        if self.run_time >= self.max_run_time:
            self.result_ready = True

    def current_speed(self) -> float:
        return max(self.min_speed, min(self.max_speed, self.forward_speed + self.speed_adjust))

    def snapshot(self) -> dict[str, float | str]:
        return {
            "impact_distance": self.impact_distance,
            "rating": self.rating,
            "drops": str(self.total_drops),
            "hits": str(self.successful_hits),
            "speed": f"{self.current_speed():.2f}",
        }

    def draw(self, screen: pygame.Surface, assets: AssetBank) -> None:
        screen.fill((11, 17, 25))
        self._draw_viewport(screen, assets)
        self._draw_hud(screen)

        if self.rating:
            text = self.fonts["title"].render(f"{self.rating}", True, (255, 223, 122))
            screen.blit(text, text.get_rect(center=(self.rect.centerx, 80)))

    def _draw_viewport(self, screen: pygame.Surface, assets: AssetBank) -> None:
        cx, cy = self.viewport_center
        r = self.viewport_radius

        # Draw black mask around circular viewport.
        pygame.draw.rect(screen, (5, 8, 12), self.rect)
        pygame.draw.circle(screen, (28, 42, 28), self.viewport_center, r)

        clip_previous = screen.get_clip()
        screen.set_clip(pygame.Rect(cx - r, cy - r, r * 2, r * 2))

        # Scrolling terrain/map effect.
        self._draw_terrain(screen, assets)

        # Draw target inside viewport coordinates.
        for target in self.targets:
            target_pos = (int(cx + target["x"]), int(cy + target["y"]))
            pygame.draw.rect(screen, (150, 120, 80), (target_pos[0] - 20, target_pos[1] - 16, 40, 32), border_radius=4)
            pygame.draw.polygon(screen, (180, 70, 70), [(target_pos[0], target_pos[1] - 26), (target_pos[0] - 16, target_pos[1] - 8), (target_pos[0] + 16, target_pos[1] - 8)])

        for effect in self.impact_effects:
            progress = effect["age"] / effect["duration"]
            if progress >= 1.0:
                continue
            ex = int(cx + effect["x"])
            ey = int(cy + effect["y"])
            if effect["kind"] == "blast":
                outer_radius = int(effect["radius"] + progress * 32)
                inner_radius = max(2, int((1.0 - progress) * 9))
                alpha = max(0, int(220 * (1.0 - progress)))

                flash = pygame.Surface((outer_radius * 2 + 2, outer_radius * 2 + 2), pygame.SRCALPHA)
                pygame.draw.circle(flash, (255, 170, 60, alpha), flash.get_rect().center, outer_radius, width=4)
                pygame.draw.circle(flash, (255, 230, 160, min(255, alpha + 25)), flash.get_rect().center, inner_radius)
                screen.blit(flash, (ex - flash.get_width() // 2, ey - flash.get_height() // 2))
            else:
                crater_radius = int(effect["radius"] * (1.0 - 0.25 * min(progress, 1.0)))
                crater = pygame.Surface((crater_radius * 2 + 6, crater_radius * 2 + 6), pygame.SRCALPHA)
                center = crater.get_rect().center
                pygame.draw.circle(crater, (45, 35, 25, 210), center, crater_radius)
                pygame.draw.circle(crater, (28, 22, 16, 220), center, max(2, crater_radius - 3), width=2)
                pygame.draw.circle(crater, (95, 80, 60, 120), (center[0] - 2, center[1] - 2), max(2, crater_radius // 2), width=1)
                screen.blit(crater, (ex - crater.get_width() // 2, ey - crater.get_height() // 2))

        # Restore clip and overlay viewport border.
        screen.set_clip(clip_previous)
        pygame.draw.circle(screen, (120, 128, 120), self.viewport_center, r, 6)

        # Fixed bombsight crosshair at center.
        pygame.draw.circle(screen, (230, 235, 230), self.viewport_center, 24, 2)
        pygame.draw.line(screen, (230, 235, 230), (cx - 52, cy), (cx + 52, cy), 2)
        pygame.draw.line(screen, (230, 235, 230), (cx, cy - 52), (cx, cy + 52), 2)

    def _draw_terrain(self, screen: pygame.Surface, assets: AssetBank) -> None:
        cx, cy = self.viewport_center
        r = self.viewport_radius

        if assets.map_bg:
            scaled = pygame.transform.smoothscale(assets.map_bg, (r * 2, r * 2))
            scroll = int((self.run_time * self.current_speed() * 30) % (r * 2))
            screen.blit(scaled, (cx - r, cy - r + scroll - r * 2))
            screen.blit(scaled, (cx - r, cy - r + scroll))
            return

        base_y = cy - r + int((self.run_time * self.current_speed() * 30) % 90)
        for i in range(-2, 12):
            y = base_y + i * 90
            pygame.draw.rect(screen, (42, 62, 42), (cx - r, y, r * 2, 46))
            pygame.draw.rect(screen, (33, 51, 33), (cx - r, y + 46, r * 2, 44))

    def _draw_hud(self, screen: pygame.Surface) -> None:
        left = self.fonts["small"].render("LEFT/RIGHT: Heading   UP: Faster   DOWN: Slower   SPACE: Release", True, (224, 224, 224))
        screen.blit(left, (40, 24))

        seconds_left = max(0, int(self.max_run_time - self.run_time))
        steady = abs(self.wind_push - self.heading_correction) < 0.18 and self.current_speed() > 0.5
        steady_color = (130, 240, 130) if steady else (230, 180, 90)

        screen.blit(self.fonts["body"].render(f"Run Clock: {seconds_left}s", True, (230, 230, 230)), (40, 62))
        screen.blit(self.fonts["body"].render(f"Drops: {self.total_drops}  Hits: {self.successful_hits}", True, (230, 230, 230)), (40, 222))
        screen.blit(self.fonts["body"].render(f"Heading Corr: {self.heading_correction:+.2f}", True, (190, 220, 255)), (40, 104))
        screen.blit(self.fonts["body"].render(f"Terrain Speed: {self.current_speed():.2f}", True, (190, 220, 255)), (40, 142))
        screen.blit(self.fonts["body"].render("Steady" if steady else "Adjusting", True, steady_color), (40, 182))
        gauge_rect = pygame.Rect(40, 258, 260, 20)
        pygame.draw.rect(screen, (70, 70, 70), gauge_rect, border_radius=6)
        fill = max(0.0, min(1.0, (self.current_speed() - self.min_speed) / (self.max_speed - self.min_speed)))
        fill_rect = gauge_rect.copy()
        fill_rect.width = max(4, int(gauge_rect.width * fill))
        color = (90, 210, 120) if self.current_speed() > self.min_speed + 0.2 else (220, 120, 70)
        pygame.draw.rect(screen, color, fill_rect, border_radius=6)
        screen.blit(self.fonts["small"].render("Speed Gauge", True, (230, 230, 230)), (40, 282))


class DebriefScene:
    def __init__(self, screen_rect: pygame.Rect, fonts: dict[str, pygame.font.Font]) -> None:
        self.rect = screen_rect
        self.fonts = fonts
        self.impact_distance = 0.0
        self.rating = ""
        self.drops = 0
        self.hits = 0

    def set_result(self, result: dict[str, float | str]) -> None:
        self.impact_distance = float(result["impact_distance"])
        self.rating = str(result["rating"])
        self.drops = int(result.get("drops", "0"))
        self.hits = int(result.get("hits", "0"))

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_RETURN):
            return True
        return False

    def draw(self, screen: pygame.Surface, _: AssetBank) -> None:
        screen.fill((236, 228, 205))
        screen.blit(self.fonts["title"].render("Bomb Run Debrief", True, (40, 40, 40)), (40, 40))
        screen.blit(self.fonts["body"].render(f"Hit Distance: {self.impact_distance:.1f} m", True, (20, 20, 20)), (44, 140))
        screen.blit(self.fonts["body"].render(f"Accuracy: {self.rating}", True, (20, 20, 20)), (44, 184))
        screen.blit(self.fonts["body"].render(f"Bombs dropped: {self.drops}   Direct hits: {self.hits}", True, (20, 20, 20)), (44, 228))

        quote = (
            "The Norden bombsight was designed for precision, but real combat conditions—wind, altitude, "
            "and enemy fire—made accuracy much more difficult."
        )
        screen.blit(self.fonts["small"].render(quote, True, (55, 55, 55)), (44, 280))
        screen.blit(self.fonts["small"].render("Press SPACE or ENTER to run another simulation.", True, (30, 30, 30)), (44, 340))


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
        self.bomb_run = BombRunScene(self.screen.get_rect(), self.fonts)
        self.debrief = DebriefScene(self.screen.get_rect(), self.fonts)
        self.scene = "assembly"

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.quit()

                if self.scene == "assembly":
                    self.assembly.handle_event(event)
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.assembly.handle_start_click(event.pos):
                        self.bomb_run.reset()
                        self.scene = "bomb_run"
                elif self.scene == "bomb_run":
                    self.bomb_run.handle_event(event)
                else:
                    if self.debrief.handle_event(event):
                        self.bomb_run.reset()
                        self.scene = "bomb_run"

            if self.scene == "assembly":
                self.assembly.update()
            elif self.scene == "bomb_run":
                self.bomb_run.update(dt)
                if self.bomb_run.result_ready:
                    self.debrief.set_result(self.bomb_run.snapshot())
                    self.scene = "debrief"

            if self.scene == "assembly":
                self.assembly.draw(self.screen, self.assets)
            elif self.scene == "bomb_run":
                self.bomb_run.draw(self.screen, self.assets)
            else:
                self.debrief.draw(self.screen, self.assets)

            pygame.display.flip()

    @staticmethod
    def quit() -> None:
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    KioskApp().run()
