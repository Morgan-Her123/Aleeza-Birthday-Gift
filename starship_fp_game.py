import math
import random
import os
import pygame

WIDTH = 960
HEIGHT = 540
FPS = 60
STAR_COUNT = 260
SPEED_SCALE = 0.5
HIT_GLOW = 0.35
LASER_LIFE = 0.18
EXPLOSION_LIFE = 0.45
LIVES_START = 10
ASTEROID_UNLOCK = 1
ASTEROID_COUNT = 0
SHIP_SPEED = 220
SHIP_BOUNDS_X = 0.98
SHIP_BOUNDS_Y = 0.92
PLANET_COUNT = 2
DOCK_COOLDOWN = 2.5
RECHARGE_PAUSE = 1.2
WARP_UNLOCK = 2
WARP_DURATION = 1.2
BEAM_HIT_COOLDOWN = 0.8

BG = (8, 10, 16)
STAR_COLORS = [(160, 180, 220), (200, 220, 255), (140, 160, 200)]
HUD = (80, 200, 220)
HUD_DARK = (20, 60, 70)
ACCENT = (255, 170, 60)
SAUCER = (120, 220, 180)
SAUCER_GLOW = (80, 140, 120)
SAUCER_HIGHLIGHT = (180, 255, 230)
SAUCER_SHADOW = (60, 120, 100)
SAUCER_SHEET = "flyingsaucer.png"
DOCK_SPRITE = "dock.jpg"
PLANET_COLORS = [
    (90, 180, 255),
    (255, 120, 200),
    (120, 240, 210),
    (255, 150, 80),
    (180, 120, 255),
    (255, 200, 120),
]
BLUE_PLANET = (70, 140, 240)
ASTEROID_COLOR = (120, 130, 140)
ASTEROID_EDGE = (80, 90, 100)
FLAME_CORE = (255, 200, 120)
FLAME_EDGE = (255, 120, 60)
PLANET_SHEET = "glowing planets.png"
ASTEROID_SHEET = "metior.jpg"
ASTEROID_BASE_TAIL_DEG = 135

WORLD_THEMES = [
    {
        "name": "Space Frontier",
        "bg": (8, 10, 16),
        "planet_palette": [(90, 180, 255), (180, 120, 255), (255, 150, 80)],
        "accent": (120, 200, 255),
    },
    {
        "name": "Green Wilds",
        "bg": (16, 38, 24),
        "planet_palette": [(70, 220, 120), (110, 255, 150), (60, 180, 90)],
        "accent": (140, 255, 170),
    },
    {
        "name": "Sky Realm",
        "bg": (110, 170, 235),
        "planet_palette": [(150, 220, 255), (190, 240, 255), (120, 200, 245)],
        "accent": (220, 245, 255),
    },
    {
        "name": "Crimson Wastes",
        "bg": (60, 20, 16),
        "planet_palette": [(220, 70, 50), (255, 110, 70), (170, 40, 30)],
        "accent": (255, 170, 120),
    },
    {
        "name": "Mythic Pastures",
        "bg": (80, 48, 92),
        "planet_palette": [(255, 130, 220), (255, 170, 240), (220, 90, 190)],
        "accent": (255, 210, 245),
    },
    {
        "name": "Deep Ocean",
        "bg": (10, 28, 70),
        "planet_palette": [(60, 130, 220), (80, 170, 240), (30, 90, 180)],
        "accent": (140, 220, 255),
    },
    {
        "name": "Violet Peaks",
        "bg": (48, 30, 80),
        "planet_palette": [(170, 110, 255), (210, 150, 255), (120, 70, 200)],
        "accent": (220, 190, 255),
    },
    {
        "name": "Golden Dunes",
        "bg": (105, 78, 24),
        "planet_palette": [(255, 220, 110), (245, 195, 80), (220, 160, 60)],
        "accent": (255, 235, 170),
    },
    {
        "name": "Ebony Arcana",
        "bg": (10, 8, 14),
        "planet_palette": [(70, 70, 90), (110, 95, 130), (55, 45, 75)],
        "accent": (185, 160, 235),
    },
]

class Star:
    def __init__(self):
        self.reset(True)

    def reset(self, far=False):
        self.x = random.uniform(-1.0, 1.0)
        self.y = random.uniform(-1.0, 1.0)
        self.z = random.uniform(0.2, 1.0) if far else random.uniform(0.05, 1.0)
        self.layer = random.choice([0.6, 0.9, 1.3])
        self.speed = random.uniform(0.35, 1.0) * self.layer
        self.color = random.choice(STAR_COLORS)

    def update(self, dt, thrust):
        self.z -= dt * self.speed * (0.55 + thrust * 1.6) * SPEED_SCALE
        if self.z <= 0.02:
            self.reset()

    def draw(self, surface):
        depth_scale = 0.35 + 0.12 * self.layer
        sx = int(WIDTH / 2 + self.x / self.z * WIDTH * depth_scale)
        sy = int(HEIGHT / 2 + self.y / self.z * HEIGHT * depth_scale)
        size = max(1, int((1.2 - self.z) * (2.2 + self.layer)))
        if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
            pygame.draw.circle(surface, self.color, (sx, sy), size)

class Beacon:
    def __init__(self, textures=None):
        self.size_scale = 1.0
        self.textures = textures or []
        self.reset()

    def reset(self):
        self.x = random.uniform(-0.25, 0.25)
        self.y = random.uniform(-0.18, 0.18)
        self.z = random.uniform(0.7, 1.0)
        self.radius = random.uniform(10, 18)

    def update(self, dt, thrust):
        self.z -= dt * (0.35 + thrust * 1.1) * SPEED_SCALE
        if self.z <= 0.08:
            self.reset()

    def draw(self, surface):
        sx = int(WIDTH / 2 + self.x / self.z * WIDTH * 0.45)
        sy = int(HEIGHT / 2 + self.y / self.z * HEIGHT * 0.45)
        radius = int(self.radius / self.z * self.size_scale)
        if 0 <= sx < WIDTH and 0 <= sy < HEIGHT:
            self._draw_saucer(surface, sx, sy, radius)

    def _draw_saucer(self, surface, sx, sy, radius):
        if self.textures:
            tex = random.choice(self.textures)
            size = max(16, int(radius * 3.0))
            sprite = pygame.transform.smoothscale(tex, (size, size))
            surface.blit(sprite, (int(sx - size / 2), int(sy - size / 2)))
            return
        body_w = max(14, int(radius * 2.6))
        body_h = max(6, int(radius * 0.9))
        dome_w = max(8, int(radius * 1.4))
        dome_h = max(5, int(radius * 0.7))

        # Glow ring
        pygame.draw.ellipse(
            surface,
            SAUCER_GLOW,
            (sx - body_w // 2 - 2, sy - body_h // 2 - 2, body_w + 4, body_h + 4),
            2,
        )
        # Main body
        pygame.draw.ellipse(
            surface,
            SAUCER,
            (sx - body_w // 2, sy - body_h // 2, body_w, body_h),
        )
        # Shadow
        pygame.draw.ellipse(
            surface,
            SAUCER_SHADOW,
            (sx - body_w // 2 + 2, sy - body_h // 2 + 1, body_w - 2, body_h - 1),
            0,
        )
        # Highlight rim
        pygame.draw.arc(
            surface,
            SAUCER_HIGHLIGHT,
            (sx - body_w // 2, sy - body_h // 2, body_w, body_h),
            math.pi * 1.05,
            math.pi * 1.9,
            2,
        )
        # Dome
        pygame.draw.ellipse(
            surface,
            (180, 240, 220),
            (sx - dome_w // 2, sy - body_h // 2 - dome_h // 2, dome_w, dome_h),
        )
        pygame.draw.ellipse(
            surface,
            (220, 255, 245),
            (sx - dome_w // 4, sy - body_h // 2 - dome_h // 2 + 1, dome_w // 2, dome_h // 2),
        )

class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Starship: First-Person Drift")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo", 18)
        self.big = pygame.font.SysFont("menlo", 36)
        self.planet_textures, self.blue_textures = self._load_planet_textures()
        self.asteroid_textures = self._load_asteroid_textures()
        self.saucer_textures = self._load_saucer_textures()
        self.dock_texture = self._load_dock_texture()
        self.stars = [Star() for _ in range(STAR_COUNT)]
        self.beacon = Beacon(self.saucer_textures)
        self.score = 0
        self.thrust = 0.0
        self.difficulty = 1.0
        self.ship_pos = [0.0, 0.18]
        self.running = True
        self.hit_timer = 0.0
        self.hit_pos = None
        self.lasers = []
        self.laser_colors = [(90, 180, 255), (255, 80, 80), (80, 240, 160)]
        self.explosions = []
        self.lives = LIVES_START
        self.asteroids = []
        self.planets = []
        self.game_over = False
        self.world_index = 0
        self.world = 1
        self.next_warp_score = WARP_UNLOCK
        self.warp_timer = 0.0
        self.warp_active = False
        self.recharge_timer = 0.0

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update(dt)
            self._draw()

        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def _update(self, dt):
        if self.game_over:
            return
        if self.recharge_timer > 0:
            self.recharge_timer = max(0.0, self.recharge_timer - dt)
            # Recharge pause: keep background world moving, disable all hits/actions.
            for star in self.stars:
                star.update(dt, 0.25)
            self._update_planets(dt)
            if self.warp_timer > 0:
                self.warp_timer = max(0.0, self.warp_timer - dt)
            return
        keys = pygame.key.get_pressed()
        self.thrust = 1.0 if keys[pygame.K_SPACE] else 0.35
        self.difficulty = 1.0 + min(self.score * 0.08, 2.0)

        mx, my = pygame.mouse.get_pos()
        nx = (mx - WIDTH / 2) / (WIDTH / 2)
        ny = (my - HEIGHT / 2) / (HEIGHT / 2)
        self.ship_pos[0] = max(-SHIP_BOUNDS_X, min(SHIP_BOUNDS_X, nx))
        self.ship_pos[1] = max(-SHIP_BOUNDS_Y, min(SHIP_BOUNDS_Y, ny))

        for star in self.stars:
            star.update(dt, self.thrust)

        self.beacon.update(dt, self.thrust)
        self.beacon.size_scale = 1.0 + min(self.score * 0.05, 1.0)

        if self.hit_timer > 0:
            self.hit_timer = max(0.0, self.hit_timer - dt)

        self._update_lasers(dt, keys[pygame.K_SPACE])
        self._update_explosions(dt)
        self._ensure_space_objects()
        self._update_asteroids(dt)
        self._update_planets(dt)
        self._check_planet_dock(dt)
        self._check_saucer_laser_hits()
        self._check_asteroid_laser_hits()
        if self.warp_timer > 0:
            self.warp_timer = max(0.0, self.warp_timer - dt)

    def _check_beacon_hit(self, laser):
        sx = int(WIDTH / 2 + self.beacon.x / self.beacon.z * WIDTH * 0.45)
        sy = int(HEIGHT / 2 + self.beacon.y / self.beacon.z * HEIGHT * 0.45)
        radius = int(self.beacon.radius / self.beacon.z)
        dx = laser["x"] - sx
        dy = laser["y"] - sy
        hit = dx * dx + dy * dy <= (radius * 0.9) ** 2 and self.beacon.z < 0.35
        if hit:
            self.hit_pos = (sx, sy)
        return hit

    def _draw(self):
        self._draw_world_background()
        for star in self.stars:
            star.draw(self.screen)
        self._draw_world_life()
        self._draw_planets()
        self._draw_asteroids()
        self.beacon.draw(self.screen)
        self._draw_lasers()
        self._draw_explosions()
        if self.hit_timer > 0 and self.hit_pos:
            self._draw_glow(self.hit_pos, self.hit_timer / HIT_GLOW)
        self._draw_ship()
        if self.warp_timer > 0:
            self._draw_warp()
        self._draw_vignette()
        self._draw_hud()
        if self.game_over:
            self._draw_game_over()
        pygame.display.flip()

    def _draw_cockpit(self):
        return

    def _draw_hud(self):
        # Readouts
        speed = int((120 + self.thrust * 80) * SPEED_SCALE)
        txt = self.font.render(f"SPEED {speed} km/s", True, HUD)
        score = self.font.render(f"SAUCERS {self.score}", True, ACCENT)
        lives = self.font.render(f"LIVES {self.lives}", True, (255, 120, 120))
        world = self._current_world_theme()["name"]
        world_txt = self.font.render(f"WORLD {world}", True, (220, 230, 240))
        tip = self.font.render("Mouse = move ship | Space = shoot", True, (180, 200, 220))
        self.screen.blit(txt, (20, 20))
        self.screen.blit(score, (20, 46))
        self.screen.blit(lives, (20, 72))
        self.screen.blit(world_txt, (20, 98))
        self.screen.blit(tip, (20, HEIGHT - 26))

    def _draw_glow(self, pos, t):
        x, y = pos
        alpha = max(0, min(1, t))
        base = 80 + int(120 * alpha)
        color = (255, base, 80)
        for r in (26, 38, 52):
            pygame.draw.circle(self.screen, color, (x, y), int(r * (0.7 + 0.5 * alpha)), 2)

    def _update_lasers(self, dt, firing):
        if firing:
            ship_x, ship_y = self._ship_screen_pos()
            cx, cy = WIDTH * 0.5, HEIGHT * 0.5
            dx = cx - ship_x
            dy = cy - ship_y
            dist = math.hypot(dx, dy) or 1.0
            vx = dx / dist * 520
            vy = dy / dist * 520
            color = self.laser_colors[len(self.lasers) % len(self.laser_colors)]
            self.lasers.append(
                {
                    "x": float(ship_x),
                    "y": float(ship_y),
                    "vx": vx,
                    "vy": vy,
                    "life": LASER_LIFE,
                    "max": LASER_LIFE,
                    "phase": random.uniform(0, math.tau),
                    "amp": random.uniform(4.0, 8.0),
                    "color": color,
                }
            )
        for beam in self.lasers:
            beam["life"] -= dt
            beam["x"] += beam["vx"] * dt
            beam["y"] += beam["vy"] * dt
        self.lasers = [b for b in self.lasers if b["life"] > 0]

    def _draw_lasers(self):
        for beam in self.lasers:
            t = beam["life"] / beam["max"]
            length = 90 * t
            color = beam.get("color", (120, 220, 255))
            x = beam["x"]
            y = beam["y"]
            dx = beam["vx"]
            dy = beam["vy"]
            dist = math.hypot(dx, dy) or 1.0
            ux = dx / dist
            uy = dy / dist
            px = -uy
            py = ux
            wobble = math.sin((1.0 - t) * 12.0 + beam["phase"]) * beam["amp"]
            head_x = x + px * wobble
            head_y = y + py * wobble
            tail_x = head_x - ux * length
            tail_y = head_y - uy * length
            # Multicolored core + glow
            glow = (min(255, color[0] + 80), min(255, color[1] + 80), min(255, color[2] + 80))
            pygame.draw.line(self.screen, glow, (head_x, head_y), (tail_x, tail_y), 4)
            pygame.draw.line(self.screen, color, (head_x, head_y), (tail_x, tail_y), 2)
            pygame.draw.line(self.screen, color, (head_x, head_y), (tail_x, tail_y), 1)

    def _check_saucer_laser_hits(self):
        if not self.lasers:
            return
        remaining = []
        hit = False
        for laser in self.lasers:
            if self._check_beacon_hit(laser):
                hit = True
            else:
                remaining.append(laser)
        self.lasers = remaining
        if hit:
            self.score += 1
            self.hit_timer = HIT_GLOW
            self._spawn_explosion(self.hit_pos)
            self.beacon.reset()
            if self.score >= self.next_warp_score:
                self._trigger_warp()
                self.next_warp_score += WARP_UNLOCK

    def _check_asteroid_laser_hits(self):
        if self.score < ASTEROID_UNLOCK or not self.lasers:
            return
        remaining = []
        for laser in self.lasers:
            destroyed = False
            for a in self.asteroids:
                sx, sy, radius = self._asteroid_screen(a)
                dx = laser["x"] - sx
                dy = laser["y"] - sy
                if dx * dx + dy * dy <= (radius * 0.9) ** 2:
                    self._spawn_explosion((sx, sy))
                    a.update(self._spawn_asteroid())
                    destroyed = True
                    break
            if not destroyed:
                remaining.append(laser)
        self.lasers = remaining

    def _spawn_explosion(self, pos):
        if not pos:
            return
        x, y = pos
        particles = []
        for _ in range(18):
            angle = random.uniform(0, math.tau)
            speed = random.uniform(80, 180)
            particles.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed,
                    "life": EXPLOSION_LIFE,
                    "max": EXPLOSION_LIFE,
                }
            )
        self.explosions.append(particles)

    def _update_explosions(self, dt):
        alive = []
        for particles in self.explosions:
            for p in particles:
                p["life"] -= dt
                p["x"] += p["vx"] * dt
                p["y"] += p["vy"] * dt
                p["vy"] += 60 * dt
            particles = [p for p in particles if p["life"] > 0]
            if particles:
                alive.append(particles)
        self.explosions = alive

    def _draw_explosions(self):
        for particles in self.explosions:
            for p in particles:
                t = p["life"] / p["max"]
                color = (255, int(140 + 80 * t), 60)
                radius = max(1, int(3 * t + 1))
                pygame.draw.circle(self.screen, color, (int(p["x"]), int(p["y"])), radius)

    def _ensure_space_objects(self):
        if self.score < ASTEROID_UNLOCK:
            return
        if not self.planets:
            for _ in range(PLANET_COUNT):
                self.planets.append(self._spawn_planet())
        if len(self.asteroids) < ASTEROID_COUNT:
            for _ in range(ASTEROID_COUNT - len(self.asteroids)):
                self.asteroids.append(self._spawn_asteroid())

    def _spawn_planet(self):
        is_blue = random.random() < 0.2
        dock_angle = random.uniform(0, math.tau)
        dock_radius = random.uniform(0.8, 1.05)
        tex_list = self.blue_textures if is_blue and self.blue_textures else self.planet_textures
        texture = random.choice(tex_list) if tex_list else None
        theme = self._current_world_theme()
        if not is_blue:
            texture = None
        return {
            "x": random.choice([random.uniform(-1.55, -1.05), random.uniform(1.05, 1.55)]),
            "y": random.uniform(-0.65, 0.3),
            "z": random.uniform(0.85, 1.35),
            "r": random.uniform(220, 340),
            "color": BLUE_PLANET if is_blue else random.choice(theme["planet_palette"]),
            "shade": random.uniform(0.4, 0.8),
            "dock": (dock_angle, dock_radius),
            "dock_cd": 0.0,
            "is_blue": is_blue,
            "tex": texture,
        }

    def _spawn_asteroid(self):
        texture = random.choice(self.asteroid_textures) if self.asteroid_textures else None
        return {
            "x": random.uniform(-0.2, 0.2),
            "y": random.uniform(-0.15, 0.15),
            "z": random.uniform(0.8, 1.2),
            "speed": random.uniform(0.35, 0.8),
            "r": random.uniform(10, 22),
            "tex": texture,
        }

    def _update_asteroids(self, dt):
        if self.score < ASTEROID_UNLOCK:
            return
        for a in self.asteroids:
            # pull toward center so they fly straight at you
            a["x"] *= 0.98
            a["y"] *= 0.98
            a["z"] -= dt * a["speed"] * (0.6 + self.thrust) * SPEED_SCALE
            if a["z"] <= 0.08:
                a.update(self._spawn_asteroid())
                continue
            sx, sy, radius = self._asteroid_screen(a)
            ship_x, ship_y = self._ship_screen_pos()
            if (ship_x - sx) ** 2 + (ship_y - sy) ** 2 <= (radius * 1.2) ** 2:
                self.lives = max(0, self.lives - 1)
                a.update(self._spawn_asteroid())
                if self.lives == 0:
                    self.game_over = True

    def _update_planets(self, dt):
        if self.score < ASTEROID_UNLOCK:
            return
        for p in self.planets:
            p["z"] -= dt * (0.15 + self.thrust * 0.25) * SPEED_SCALE
            if p["dock_cd"] > 0:
                p["dock_cd"] = max(0.0, p["dock_cd"] - dt)
            if p["z"] <= 0.2:
                p.update(self._spawn_planet())

    def _draw_planets(self):
        if self.score < ASTEROID_UNLOCK:
            return
        for p in self.planets:
            sx, sy, radius = self._planet_screen(p)
            if p.get("tex"):
                tex = p["tex"]
                size = max(8, int(radius * 2.0))
                planet = pygame.transform.smoothscale(tex, (size, size))
                self.screen.blit(planet, (int(sx - size / 2), int(sy - size / 2)))
            else:
                base = p["color"]
                shade = int(60 * p["shade"])
                highlight = (min(255, base[0] + shade), min(255, base[1] + shade), min(255, base[2] + shade))
                shadow = (max(0, base[0] - shade), max(0, base[1] - shade), max(0, base[2] - shade))
                pygame.draw.circle(self.screen, base, (int(sx), int(sy)), int(radius))
                pygame.draw.circle(self.screen, shadow, (int(sx + radius * 0.18), int(sy + radius * 0.18)), int(radius * 0.95))
                pygame.draw.circle(self.screen, highlight, (int(sx - radius * 0.22), int(sy - radius * 0.22)), int(radius * 0.6))
                ring = (180, 210, 230) if not p["is_blue"] else (120, 200, 255)
                pygame.draw.circle(self.screen, ring, (int(sx), int(sy)), int(radius * 1.03), 1)
            # Docking point
            dock_x, dock_y = self._planet_dock_screen(p, sx, sy, radius)
            dock_color = (120, 200, 255) if p["is_blue"] else (180, 180, 180)
            if p["is_blue"]:
                angle, _ = p["dock"]
                conn_x = sx + math.cos(angle) * radius * 0.58
                conn_y = sy + math.sin(angle) * radius * 0.58
                pygame.draw.line(self.screen, (120, 200, 255), (conn_x, conn_y), (dock_x, dock_y), 3)
                if self.dock_texture:
                    dock_size = max(24, int(radius * 0.22))
                    dock_sprite = pygame.transform.smoothscale(self.dock_texture, (dock_size, dock_size))
                    self.screen.blit(dock_sprite, (int(dock_x - dock_size / 2), int(dock_y - dock_size / 2)))
                else:
                    dock_w = max(18, int(radius * 0.35))
                    dock_h = max(10, int(radius * 0.12))
                    pygame.draw.ellipse(
                        self.screen,
                        dock_color,
                        (dock_x - dock_w / 2, dock_y - dock_h / 2, dock_w, dock_h),
                        2,
                    )
                    pygame.draw.ellipse(
                        self.screen,
                        (200, 240, 255),
                        (dock_x - dock_w / 3, dock_y - dock_h / 3, dock_w * 0.66, dock_h * 0.66),
                        1,
                    )
            else:
                pygame.draw.circle(self.screen, dock_color, (int(dock_x), int(dock_y)), max(2, int(radius * 0.08)))
                pygame.draw.circle(self.screen, (80, 70, 40), (int(dock_x), int(dock_y)), max(3, int(radius * 0.12)), 1)
            pygame.draw.circle(self.screen, (20, 30, 40), (int(sx), int(sy)), int(radius), 2)

    def _draw_asteroids(self):
        if self.score < ASTEROID_UNLOCK:
            return
        for a in self.asteroids:
            x, y, radius = self._asteroid_screen(a)
            if a.get("tex"):
                size = max(12, int(radius * 3.0))
                sprite = pygame.transform.smoothscale(a["tex"], (size, size))
                # Rotate so tail points away from center (behind the meteor)
                cx, cy = WIDTH / 2, HEIGHT / 2
                angle = math.degrees(math.atan2(y - cy, x - cx))
                rotate = angle - ASTEROID_BASE_TAIL_DEG
                sprite = pygame.transform.rotate(sprite, rotate)
                self.screen.blit(sprite, (int(x - size / 2), int(y - size / 2)))
            else:
                self._draw_asteroid(int(x), int(y), int(radius))
                self._draw_asteroid_flame(int(x), int(y), int(radius))

    def _asteroid_screen(self, a):
        sx = WIDTH / 2 + a["x"] / a["z"] * WIDTH * 0.45
        sy = HEIGHT / 2 + a["y"] / a["z"] * HEIGHT * 0.45
        radius = a["r"] / a["z"]
        return sx, sy, radius

    def _planet_screen(self, p):
        sx = WIDTH / 2 + p["x"] / p["z"] * WIDTH * 0.35
        sy = HEIGHT / 2 + p["y"] / p["z"] * HEIGHT * 0.35
        radius = p["r"] / p["z"]
        return sx, sy, radius

    def _planet_dock_screen(self, p, sx, sy, radius):
        angle, dist = p["dock"]
        dx = math.cos(angle) * radius * dist
        dy = math.sin(angle) * radius * dist
        return sx + dx, sy + dy

    def _draw_asteroid(self, x, y, radius):
        if radius <= 2:
            pygame.draw.circle(self.screen, ASTEROID_COLOR, (x, y), radius)
            return
        points = []
        sides = 8
        for i in range(sides):
            angle = (math.tau / sides) * i
            jitter = random.uniform(0.65, 1.15)
            px = x + math.cos(angle) * radius * jitter
            py = y + math.sin(angle) * radius * jitter
            points.append((px, py))
        pygame.draw.polygon(self.screen, ASTEROID_COLOR, points)
        pygame.draw.polygon(self.screen, ASTEROID_EDGE, points, 2)
        # Highlight/shadow for depth
        pygame.draw.circle(self.screen, (150, 160, 170), (x - radius // 4, y - radius // 4), max(2, radius // 3), 1)
        pygame.draw.circle(self.screen, (60, 70, 80), (x + radius // 5, y + radius // 5), max(2, radius // 3), 1)
        # Craters for depth
        for _ in range(3):
            cx = x + random.randint(-radius // 2, radius // 2)
            cy = y + random.randint(-radius // 2, radius // 2)
            cr = max(2, radius // 5)
            pygame.draw.circle(self.screen, ASTEROID_EDGE, (cx, cy), cr, 1)

    def _draw_asteroid_flame(self, x, y, radius):
        length = int(radius * 2.2)
        tail_x = x
        tail_y = y + length
        pygame.draw.line(self.screen, FLAME_EDGE, (x, y + radius), (tail_x, tail_y), max(2, radius // 3))
        pygame.draw.line(self.screen, FLAME_CORE, (x, y + radius), (tail_x, y + length * 0.7), max(1, radius // 4))

    def _ship_screen_pos(self):
        sx = WIDTH / 2 + self.ship_pos[0] * WIDTH * 0.5
        sy = HEIGHT / 2 + self.ship_pos[1] * HEIGHT * 0.5
        return sx, sy

    def _draw_ship(self):
        sx, sy = self._ship_screen_pos()
        points = [
            (sx, sy - 10),
            (sx - 8, sy + 10),
            (sx + 8, sy + 10),
        ]
        pygame.draw.polygon(self.screen, HUD, points, 0)
        pygame.draw.polygon(self.screen, (200, 240, 255), points, 1)

    def _draw_game_over(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))
        title = self.big.render("GAME OVER", True, (255, 120, 120))
        subtitle = self.font.render("Press Esc to quit", True, (220, 220, 220))
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT * 0.42))
        self.screen.blit(subtitle, (WIDTH // 2 - subtitle.get_width() // 2, HEIGHT * 0.52))

    def _draw_vignette(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 0))
        alpha = 70
        pygame.draw.rect(overlay, (0, 0, 0, alpha), (0, 0, WIDTH, 60))
        pygame.draw.rect(overlay, (0, 0, 0, alpha), (0, HEIGHT - 70, WIDTH, 70))
        pygame.draw.rect(overlay, (0, 0, 0, alpha), (0, 0, 70, HEIGHT))
        pygame.draw.rect(overlay, (0, 0, 0, alpha), (WIDTH - 70, 0, 70, HEIGHT))
        self.screen.blit(overlay, (0, 0))

    def _load_planet_textures(self):
        path = os.path.join(os.path.dirname(__file__), PLANET_SHEET)
        if not os.path.exists(path):
            return [], []
        sheet = pygame.image.load(path).convert_alpha()
        cols = 4
        rows = 2
        w = sheet.get_width() // cols
        h = sheet.get_height() // rows
        textures = []
        blueish = []
        for r in range(rows):
            for c in range(cols):
                rect = pygame.Rect(c * w, r * h, w, h)
                sub = sheet.subsurface(rect).copy()
                textures.append(sub)
        # Mark a subset as blue-ish for recharge planets
        for idx in (0, 1, 5, 7):
            if idx < len(textures):
                blueish.append(textures[idx])
        return textures, blueish

    def _load_asteroid_textures(self):
        path = os.path.join(os.path.dirname(__file__), ASTEROID_SHEET)
        if not os.path.exists(path):
            return []
        sheet = pygame.image.load(path).convert_alpha()
        return [sheet]

    def _load_saucer_textures(self):
        path = os.path.join(os.path.dirname(__file__), SAUCER_SHEET)
        if not os.path.exists(path):
            return []
        sheet = pygame.image.load(path).convert_alpha()
        return [sheet]

    def _load_dock_texture(self):
        path = os.path.join(os.path.dirname(__file__), DOCK_SPRITE)
        if not os.path.exists(path):
            return None
        return pygame.image.load(path).convert_alpha()

    def _check_planet_dock(self, dt):
        if self.score < ASTEROID_UNLOCK:
            return
        ship_x, ship_y = self._ship_screen_pos()
        for p in self.planets:
            if p["dock_cd"] > 0:
                continue
            if not p["is_blue"]:
                continue
            sx, sy, radius = self._planet_screen(p)
            dock_x, dock_y = self._planet_dock_screen(p, sx, sy, radius)
            dx = ship_x - dock_x
            dy = ship_y - dock_y
            if dx * dx + dy * dy <= (radius * 0.2) ** 2:
                self.lives = min(LIVES_START, self.lives + 2)
                p["dock_cd"] = DOCK_COOLDOWN
                self.recharge_timer = RECHARGE_PAUSE

    def _trigger_warp(self):
        self.warp_active = True
        self.warp_timer = WARP_DURATION
        self.world_index = (self.world_index + 1) % len(WORLD_THEMES)
        self.world = self.world_index + 1
        # refresh the universe
        self.stars = [Star() for _ in range(STAR_COUNT)]
        self.asteroids = []
        self.planets = []
        self._ensure_space_objects()
        self.recharge_timer = 0.0

    def _draw_warp(self):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        strength = self.warp_timer / WARP_DURATION
        alpha = int(200 * strength)
        overlay.fill((255, 210, 90, alpha))
        self.screen.blit(overlay, (0, 0))
        # radial pull lines
        cx, cy = self._ship_screen_pos()
        for i in range(18):
            angle = (math.tau / 18) * i
            length = 60 + strength * 120
            x2 = cx + math.cos(angle) * length
            y2 = cy + math.sin(angle) * length
            pygame.draw.line(self.screen, (255, 245, 180), (cx, cy), (x2, y2), 2)

    def _current_world_theme(self):
        return WORLD_THEMES[self.world_index % len(WORLD_THEMES)]

    def _draw_world_background(self):
        theme = self._current_world_theme()
        self.screen.fill(theme["bg"])

    def _draw_world_life(self):
        # Lightweight themed cues for each world.
        idx = self.world_index
        if idx == 2:
            for i in range(6):
                x = (i * 180 + (pygame.time.get_ticks() * 0.02)) % (WIDTH + 120) - 120
                pygame.draw.ellipse(self.screen, (210, 235, 255), (x, 70 + (i % 3) * 42, 140, 38))
        elif idx == 3:
            for i in range(5):
                x = i * 220 + 30
                pygame.draw.circle(self.screen, (255, 90, 50), (x % WIDTH, HEIGHT - 40), 20)
        elif idx == 4:
            for i in range(8):
                x = (i * 130 + pygame.time.get_ticks() * 0.04) % WIDTH
                y = HEIGHT - 80 - (i % 3) * 20
                pygame.draw.ellipse(self.screen, (130, 240, 150), (x, y, 22, 10))
        elif idx == 5:
            for i in range(10):
                x = (i * 95 + pygame.time.get_ticks() * 0.03) % WIDTH
                y = HEIGHT - 130 + (i % 5) * 12
                pygame.draw.arc(self.screen, (120, 220, 255), (x, y, 40, 24), 0.1, 2.8, 2)
        elif idx == 6:
            for i in range(7):
                x = i * 140
                peak = 180 + (i % 3) * 25
                pygame.draw.polygon(self.screen, (110, 95, 160), [(x, HEIGHT), (x + 70, HEIGHT - peak), (x + 140, HEIGHT)])
        elif idx == 7:
            pygame.draw.rect(self.screen, (200, 160, 70), (0, HEIGHT - 140, WIDTH, 140))
        elif idx == 8:
            pygame.draw.rect(self.screen, (20, 18, 28), (0, HEIGHT - 180, WIDTH, 180))
            for i in range(4):
                x = 120 + i * 220
                pygame.draw.rect(self.screen, (35, 30, 45), (x, HEIGHT - 240, 70, 180))


def main():
    Game().run()


if __name__ == "__main__":
    main()
