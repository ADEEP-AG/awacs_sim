# awacs_sim

import pygame
import math
import random
import time

# Initialize Pygame
pygame.init()

# Screen settings
RESOLUTIONS = [(1920, 1080), (1366, 768), (1280, 720)]
current_res_index = 0
WIDTH, HEIGHT = RESOLUTIONS[current_res_index]
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("E-3 Sentry AWACS Sim: Next Level")

# Colors
BG_DARK = (10, 15, 20)
FRAME_GRAY = (30, 40, 50)
ACCENT_BLUE = (70, 130, 200)
GREEN = (80, 240, 80)
RED = (240, 60, 60)
YELLOW = (240, 240, 80)
WHITE = (200, 210, 220)
CYAN = (80, 240, 240)
ORANGE = (240, 120, 40)
DARK_GREEN = (40, 80, 40)
PURPLE = (150, 80, 240)
MAGENTA = (240, 80, 240)  # For interceptors

# Radar settings
def update_radar_settings(w, h):
    global RADAR_CENTER, RADAR_RADIUS, HUD_WIDTH, MINI_MAP_SIZE, ALT_GRAPH_SIZE, LOG_HEIGHT
    RADAR_CENTER = (w // 2 - int(w * 0.2), h // 2)
    RADAR_RADIUS = int(min(w, h) * 0.55)
    HUD_WIDTH = int(w * 0.4)
    MINI_MAP_SIZE = int(min(w, h) * 0.18)
    ALT_GRAPH_SIZE = (int(HUD_WIDTH * 0.5), int(h * 0.14))
    LOG_HEIGHT = int(h * 0.25)

update_radar_settings(WIDTH, HEIGHT)
sweep_angle = 0
sweep_speed = 1.2
zoom_level = 1.0
jamming_active = False
radar_mode = "SEARCH"
weather_active = False
lock_warning = False
elint_active = False
flare_active = False
intercept_active = False
airspace_status = "GREEN"  # GREEN, YELLOW, RED

# Target class with classification and interceptors
class Target:
    AIRCRAFT_TYPES = {
        "FRIEND": ["F-16", "F-22", "C-130"],
        "HOSTILE": ["MiG-29", "Su-35", "Tu-95"],
        "UNKNOWN": ["Unknown"],
        "CIVILIAN": ["Boeing 737", "Airbus A320"],
        "MISSILE": ["SAM", "Cruise"],
        "INTERCEPTOR": ["AIM-120"]
    }

    def __init__(self, is_missile=False, is_interceptor=False):
        self.angle = random.uniform(0, 360)
        self.distance = random.randint(150, RADAR_RADIUS) if not is_interceptor else RADAR_RADIUS
        self.speed = random.uniform(8, 20) if is_missile else random.uniform(20, 30) if is_interceptor else random.uniform(1, 5)
        self.altitude = random.randint(500, 6000) if is_missile or is_interceptor else random.randint(10000, 45000)
        self.heading = random.uniform(0, 360)
        self.type = "INTERCEPTOR" if is_interceptor else "MISSILE" if is_missile else random.choice(["FRIEND", "HOSTILE", "UNKNOWN", "CIVILIAN"])
        self.model = random.choice(self.AIRCRAFT_TYPES[self.type]) if self.type != "UNKNOWN" else "Unknown"
        self.color = MAGENTA if is_interceptor else CYAN if is_missile else GREEN if self.type == "FRIEND" else RED if self.type == "HOSTILE" else YELLOW if self.type == "UNKNOWN" else WHITE
        self.trail = []
        self.alt_history = []
        self.last_sweep = -1
        self.iff_status = "PENDING" if self.type == "UNKNOWN" and not is_missile else self.type
        self.jammed = False
        self.locked = False
        self.flared = False
        self.target = None  # For interceptors
        self.radar_cross_section = 0.05 if is_interceptor else random.uniform(0.5, 5.0) if not is_missile else 0.1
        self.elint_signature = 0 if is_interceptor else random.randint(100, 500) if not is_missile else 50
        self.threat_level = "LOW" if self.type in ["FRIEND", "CIVILIAN"] else random.choice(["MED", "HIGH"]) if not is_missile else "CRITICAL" if not is_interceptor else "DEFENSE"

    def update(self):
        if not self.jammed:
            if self.type == "INTERCEPTOR" and self.target:
                target_x = RADAR_CENTER[0] + self.target.distance * math.cos(math.radians(self.target.angle))
                target_y = RADAR_CENTER[1] - self.target.distance * math.sin(math.radians(self.target.angle))
                self_x = RADAR_CENTER[0] + self.distance * math.cos(math.radians(self.angle))
                self_y = RADAR_CENTER[1] - self.distance * math.sin(math.radians(self.angle))
                angle_to_target = math.degrees(math.atan2(target_y - self_y, target_x - self_x))
                self.heading = angle_to_target
                if math.hypot(self_x - target_x, self_y - target_y) < 20:
                    self.target = None  # Interceptor hit
            self.angle += self.speed * math.cos(math.radians(self.heading - self.angle)) * 0.08
            self.distance += self.speed * math.sin(math.radians(self.heading - self.angle)) * 0.08
            self.angle %= 360
            self.distance = max(100, min(RADAR_RADIUS, self.distance))
            if self.type == "INTERCEPTOR" and self.distance < 100:
                self.distance = RADAR_RADIUS  # Respawn interceptor
            self.altitude += random.randint(-150, 150) if self.type not in ["MISSILE", "INTERCEPTOR"] else 0
            self.altitude = max(500, min(50000, self.altitude))
            if random.random() < 0.04:
                x = RADAR_CENTER[0] + self.distance * math.cos(math.radians(self.angle))
                y = RADAR_CENTER[1] - self.distance * math.sin(math.radians(self.angle))
                self.trail.append((x, y))
                self.alt_history.append(self.altitude)
                if len(self.trail) > 15:
                    self.trail.pop(0)
                if len(self.alt_history) > 50:
                    self.alt_history.pop(0)
            if self.flared and random.random() < 0.1:
                self.jammed = True

    def draw(self, screen, sweep_angle, zoom, mode):
        if mode == "TRACK" and self != selected_target:
            return
        if abs(self.angle - sweep_angle) < 35 or abs(self.angle - sweep_angle + 360) < 35:
            self.last_sweep = pygame.time.get_ticks()
        if pygame.time.get_ticks() - self.last_sweep < 6000:
            x = RADAR_CENTER[0] + self.distance * math.cos(math.radians(self.angle)) * zoom
            y = RADAR_CENTER[1] - self.distance * math.sin(math.radians(self.angle)) * zoom
            if self.jammed and random.random() < 0.8:
                return
            if self.type in ["MISSILE", "INTERCEPTOR"]:
                shape = pygame.Rect(int(x) - 10, int(y) - 10, 20, 20)
                pygame.draw.rect(screen, self.color, shape, 2)
            else:
                points = [
                    (x + 15 * math.cos(math.radians(self.heading)), y - 15 * math.sin(math.radians(self.heading))),
                    (x + 10 * math.cos(math.radians(self.heading + 150)), y - 10 * math.sin(math.radians(self.heading + 150))),
                    (x + 10 * math.cos(math.radians(self.heading - 150)), y - 10 * math.sin(math.radians(self.heading - 150)))
                ]
                pygame.draw.polygon(screen, self.color, points, 2)
            if self.locked:
                pygame.draw.circle(screen, ORANGE, (int(x), int(y)), 20, 3)
            if self.flared:
                pygame.draw.circle(screen, YELLOW, (int(x), int(y)), 25, 2)
            font = pygame.font.SysFont("consolas", int(16 * WIDTH / 1920))
            label = font.render(f"{self.iff_status[0]}{id(self)%100}", True, WHITE)
            screen.blit(label, (int(x) + 25, int(y) - 25))
            for i, (tx, ty) in enumerate(self.trail):
                alpha = int(255 * (1 - i / len(self.trail)))
                pygame.draw.circle(screen, (*self.color[:2], alpha), (int(tx * zoom), int(ty * zoom)), 5)
            if self == selected_target:
                for i in range(7):
                    pred_x = x + i * 15 * self.speed * math.cos(math.radians(self.heading)) * zoom
                    pred_y = y - i * 15 * self.speed * math.sin(math.radians(self.heading)) * zoom
                    pygame.draw.circle(screen, (self.color[0], self.color[1], self.color[2], 80), (int(pred_x), int(pred_y)), 4)

# Create targets
targets = [Target() for _ in range(20)] + [Target(is_missile=True) for _ in range(5)] + [Target(is_interceptor=True) for _ in range(2)]

# Sound
try:
    pygame.mixer.init()
    sample_rate = 44100
    duration = 0.1
    samples = int(sample_rate * duration)
    beep_array = bytearray([int(128 + 127 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(samples)] * 2)
    warning_array = bytearray([int(128 + 127 * math.sin(2 * math.pi * 880 * i / sample_rate)) for i in range(samples * 3)] * 2)
    flare_array = bytearray([int(128 + 127 * math.sin(2 * math.pi * 660 * i / sample_rate)) for i in range(samples * 2)] * 2)
    intercept_array = bytearray([int(128 + 127 * math.sin(2 * math.pi * 1000 * i / sample_rate)) for i in range(samples * 2)] * 2)
    beep = pygame.mixer.Sound(buffer=beep_array)
    warning_beep = pygame.mixer.Sound(buffer=warning_array)
    flare_sound = pygame.mixer.Sound(buffer=flare_array)
    intercept_sound = pygame.mixer.Sound(buffer=intercept_array)
except Exception as e:
    print(f"Audio initialization failed: {e}")
    beep, warning_beep, flare_sound, intercept_sound = None, None, None, None

# UI elements
def update_ui_elements():
    global earth_map, weather, mini_map, radar_noise, altitude_graph, command_log
    earth_map = pygame.Surface((RADAR_RADIUS * 2, RADAR_RADIUS * 2), pygame.SRCALPHA)
    for _ in range(60):
        pygame.draw.line(earth_map, DARK_GREEN, 
                         (random.randint(0, RADAR_RADIUS * 2), random.randint(0, RADAR_RADIUS * 2)),
                         (random.randint(0, RADAR_RADIUS * 2), random.randint(0, RADAR_RADIUS * 2)), 3)
    weather = pygame.Surface((RADAR_RADIUS * 2, RADAR_RADIUS * 2), pygame.SRCALPHA)
    for _ in range(300):
        pygame.draw.circle(weather, (CYAN[0], CYAN[1], CYAN[2], 70), 
                           (random.randint(0, RADAR_RADIUS * 2), random.randint(0, RADAR_RADIUS * 2)), 
                           random.randint(40, 80))
    mini_map = pygame.Surface((MINI_MAP_SIZE, MINI_MAP_SIZE), pygame.SRCALPHA)
    radar_noise = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    altitude_graph = pygame.Surface(ALT_GRAPH_SIZE, pygame.SRCALPHA)
    command_log = pygame.Surface((HUD_WIDTH - 20, LOG_HEIGHT), pygame.SRCALPHA)

update_ui_elements()
log_entries = []

# Main loop
running = True
clock = pygame.time.Clock()
selected_target = None
start_time = time.time()

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            # HUD buttons
            if WIDTH - HUD_WIDTH + 50 <= mx <= WIDTH - HUD_WIDTH + 250:
                if 150 <= my <= 200:  # Mode
                    radar_mode = "TRACK" if radar_mode == "SEARCH" else "SEARCH"
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] Mode set to {radar_mode}")
                elif 220 <= my <= 270:  # IFF
                    if selected_target:
                        old_status = selected_target.iff_status
                        selected_target.iff_status = random.choice(["FRIEND", "HOSTILE"]) if selected_target.iff_status == "PENDING" else selected_target.iff_status
                        selected_target.color = GREEN if selected_target.iff_status == "FRIEND" else RED
                        log_entries.append(f"[{time.strftime('%H:%M:%S')}] IFF: {selected_target.model} changed from {old_status} to {selected_target.iff_status}")
                elif 280 <= my <= 330:  # Jam
                    jamming_active = not jamming_active
                    for target in targets:
                        target.jammed = jamming_active and random.random() < 0.6
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] Jamming {'enabled' if jamming_active else 'disabled'}")
                elif 340 <= my <= 390:  # Weather
                    weather_active = not weather_active
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] Weather radar {'enabled' if weather_active else 'disabled'}")
                elif 400 <= my <= 450:  # Lock
                    if selected_target:
                        selected_target.locked = not selected_target.locked
                        lock_warning = selected_target.locked and selected_target.threat_level in ["HIGH", "CRITICAL"]
                        log_entries.append(f"[{time.strftime('%H:%M:%S')}] {selected_target.model} {'locked' if selected_target.locked else 'unlocked'}")
                elif 460 <= my <= 510:  # ELINT
                    elint_active = not elint_active
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] ELINT {'enabled' if elint_active else 'disabled'}")
                elif 520 <= my <= 570:  # Flare
                    flare_active = not flare_active
                    if flare_active and flare_sound:
                        flare_sound.play()
                    for target in targets:
                        target.flared = flare_active and random.random() < 0.3
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] Flares {'deployed' if flare_active else 'disabled'}")
                elif 580 <= my <= 630:  # Intercept
                    intercept_active = not intercept_active
                    if intercept_active and intercept_sound:
                        intercept_sound.play()
                    if selected_target and selected_target.threat_level in ["HIGH", "CRITICAL"]:
                        for t in targets:
                            if t.type == "INTERCEPTOR" and t.target is None:
                                t.target = selected_target
                                log_entries.append(f"[{time.strftime('%H:%M:%S')}] Interceptor launched at {selected_target.model}")
                                break
                elif 640 <= my <= 690:  # Resolution
                    current_res_index = (current_res_index + 1) % len(RESOLUTIONS)
                    WIDTH, HEIGHT = RESOLUTIONS[current_res_index]
                    screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                    update_radar_settings(WIDTH, HEIGHT)
                    update_ui_elements()
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] Resolution changed to {WIDTH}x{HEIGHT}")
            # Target selection
            for target in targets:
                x = RADAR_CENTER[0] + target.distance * math.cos(math.radians(target.angle)) * zoom_level
                y = RADAR_CENTER[1] - target.distance * math.sin(math.radians(target.angle)) * zoom_level
                if math.hypot(mx - x, my - y) < 25:
                    selected_target = target
                    log_entries.append(f"[{time.strftime('%H:%M:%S')}] Selected {selected_target.model}")
                    break
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                zoom_level = min(5.0, zoom_level + 0.5)
            elif event.key == pygame.K_MINUS:
                zoom_level = max(0.1, zoom_level - 0.5)

    # Update airspace status
    hostile_count = sum(1 for t in targets if t.threat_level in ["HIGH", "CRITICAL"] and pygame.time.get_ticks() - t.last_sweep < 6000)
    airspace_status = "RED" if hostile_count > 3 else "YELLOW" if hostile_count > 0 else "GREEN"

    # Clear screen
    screen.fill(BG_DARK)

    # Draw earth map
    map_rotated = pygame.transform.rotate(earth_map, sweep_angle / 20)
    map_rect = map_rotated.get_rect(center=RADAR_CENTER)
    screen.blit(map_rotated, map_rect)

    # Draw weather
    if weather_active:
        weather_rotated = pygame.transform.rotate(weather, sweep_angle / 25)
        weather_rect = weather_rotated.get_rect(center=RADAR_CENTER)
        screen.blit(weather_rotated, weather_rect)

    # Draw radar noise
    radar_noise.fill((0, 0, 0, 0))
    for _ in range(int(250 * WIDTH / 1920) if jamming_active else int(120 * WIDTH / 1920)):
        nx, ny = random.randint(0, WIDTH), random.randint(0, HEIGHT)
        pygame.draw.circle(radar_noise, (GREEN[0], GREEN[1], GREEN[2], 30 if jamming_active else 15), (nx, ny), 3)
    screen.blit(radar_noise, (0, 0))

    # Draw radar grid
    pygame.draw.rect(screen, FRAME_GRAY, (0, 0, WIDTH, HEIGHT), int(12 * WIDTH / 1920))
    for r in range(100, int(RADAR_RADIUS * zoom_level) + 1, 100):
        pygame.draw.circle(screen, DARK_GREEN, RADAR_CENTER, r, 5 if r % 300 == 0 else 2)
        if r % 300 == 0:
            text = pygame.font.SysFont("consolas", int(14 * WIDTH / 1920)).render(f"{r}nm", True, WHITE)
            screen.blit(text, (RADAR_CENTER[0] + r * zoom_level + 5, RADAR_CENTER[1] - 20))
    for angle in range(0, 360, 5):
        x = RADAR_CENTER[0] + RADAR_RADIUS * zoom_level * math.cos(math.radians(angle))
        y = RADAR_CENTER[1] - RADAR_RADIUS * zoom_level * math.sin(math.radians(angle))
        pygame.draw.line(screen, DARK_GREEN, RADAR_CENTER, (x, y), 3 if angle % 30 == 0 else 1)
        if angle % 30 == 0:
            text = pygame.font.SysFont("consolas", int(14 * WIDTH / 1920)).render(f"{angle}°", True, WHITE)
            screen.blit(text, (x + 5, y - 5))

    # Draw sweep line
    sweep_end_x = RADAR_CENTER[0] + RADAR_RADIUS * zoom_level * math.cos(math.radians(sweep_angle))
    sweep_end_y = RADAR_CENTER[1] - RADAR_RADIUS * zoom_level * math.sin(math.radians(sweep_angle))
    pygame.draw.line(screen, ACCENT_BLUE, RADAR_CENTER, (sweep_end_x, sweep_end_y), int(8 * WIDTH / 1920))
    if beep and sweep_angle % 120 < sweep_speed:
        beep.play()
    if lock_warning and warning_beep and int(time.time() * 2) % 2 == 0:
        warning_beep.play()
    sweep_angle = (sweep_angle + sweep_speed) % 360

    # Update and draw targets
    for target in targets:
        target.update()
        target.draw(screen, sweep_angle, zoom_level, radar_mode)

    # Draw mini-map
    mini_map.fill((BG_DARK[0], BG_DARK[1], BG_DARK[2], 220))
    pygame.draw.circle(mini_map, DARK_GREEN, (MINI_MAP_SIZE // 2, MINI_MAP_SIZE // 2), MINI_MAP_SIZE // 2 - 5, 3)
    for r in range(50, MINI_MAP_SIZE // 2 - 4, 50):
        pygame.draw.circle(mini_map, DARK_GREEN, (MINI_MAP_SIZE // 2, MINI_MAP_SIZE // 2), r, 1)
    for target in targets:
        if pygame.time.get_ticks() - target.last_sweep < 6000:
            mx = MINI_MAP_SIZE // 2 + (target.distance / RADAR_RADIUS) * (MINI_MAP_SIZE // 2 - 5) * math.cos(math.radians(target.angle))
            my = MINI_MAP_SIZE // 2 - (target.distance / RADAR_RADIUS) * (MINI_MAP_SIZE // 2 - 5) * math.sin(math.radians(target.angle))
            pygame.draw.circle(mini_map, target.color, (int(mx), int(my)), 5)
    mini_rect = mini_map.get_rect(topleft=(WIDTH - HUD_WIDTH - MINI_MAP_SIZE - 20, HEIGHT - MINI_MAP_SIZE - LOG_HEIGHT - 40))
    screen.blit(mini_map, mini_rect)

    # Draw HUD
    pygame.draw.rect(screen, FRAME_GRAY, (WIDTH - HUD_WIDTH, 0, HUD_WIDTH, HEIGHT), border_radius=15)
    pygame.draw.rect(screen, BG_DARK, (WIDTH - HUD_WIDTH + 10, 10, HUD_WIDTH - 20, HEIGHT - 20), border_radius=10)
    elapsed_time = int(time.time() - start_time)
    hud = [
        "E-3 SENTRY AWACS",
        f"ZOOM: {zoom_level:.1f}x",
        f"SWEEP: {int(sweep_angle)}°",
        f"TARGETS: {len(targets)} (M: {sum(1 for t in targets if t.type == 'MISSILE')})",
        f"MODE: {radar_mode}",
        f"JAMMING: {'ON' if jamming_active else 'OFF'}",
        f"WEATHER: {'ON' if weather_active else 'OFF'}",
        f"LOCK: {'ACTIVE' if lock_warning else 'OFF'}",
        f"ELINT: {'ON' if elint_active else 'OFF'}",
        f"FLARE: {'ON' if flare_active else 'OFF'}",
        f"INTERCEPT: {'ON' if intercept_active else 'OFF'}",
        f"RES: {WIDTH}x{HEIGHT}",
        f"AIRSPACE: {airspace_status}",
        f"TIME: {elapsed_time//3600:02d}:{(elapsed_time%3600)//60:02d}:{elapsed_time%60:02d}",
        "CONTROLS: [+/-] ZOOM | CLICK TARGETS & BUTTONS"
    ]
    font = pygame.font.SysFont("consolas", int(20 * WIDTH / 1920))
    small_font = pygame.font.SysFont("consolas", int(14 * WIDTH / 1920))
    for i, line in enumerate(hud):
        text = font.render(line, True, GREEN if "GREEN" in line else YELLOW if "YELLOW" in line else RED if "RED" in line else WHITE)
        screen.blit(text, (WIDTH - HUD_WIDTH + 30, 20 + i * 45))
    # Buttons
    buttons = ["MODE", "IFF", "JAM", "WXR", "LOCK", "ELINT", "FLARE", "INCPT", "RES"]
    for i, label in enumerate(buttons):
        color = ACCENT_BLUE if (i == 0 and radar_mode == "TRACK") or (i == 2 and jamming_active) or (i == 3 and weather_active) or (i == 4 and lock_warning) or (i == 5 and elint_active) or (i == 6 and flare_active) or (i == 7 and intercept_active) else FRAME_GRAY
        pygame.draw.rect(screen, color, (WIDTH - HUD_WIDTH + 50, 150 + i * 70, 200, 50), border_radius=8)
        text = font.render(label, True, WHITE)
        screen.blit(text, (WIDTH - HUD_WIDTH + 90, 160 + i * 70))

    # Selected target info
    if selected_target:
        info = [
            f"ID: {selected_target.iff_status[0]}{id(selected_target)%100}",
            f"TYPE: {selected_target.iff_status}",
            f"MODEL: {selected_target.model}",
            f"ALT: {selected_target.altitude}ft",
            f"SPD: {int(selected_target.speed * (600 if selected_target.type in ['MISSILE', 'INTERCEPTOR'] else 200))}kt",
            f"HDG: {int(selected_target.heading)}°",
            f"BRG: {int(selected_target.angle)}°",
            f"RNG: {int(selected_target.distance)}nm",
            f"DETECT: {(pygame.time.get_ticks() - selected_target.last_sweep)//1000}s ago",
            f"JAMMED: {'YES' if selected_target.jammed else 'NO'}",
            f"LOCKED: {'YES' if selected_target.locked else 'NO'}",
            f"FLARED: {'YES' if selected_target.flared else 'NO'}",
            f"RCS: {selected_target.radar_cross_section:.1f}m²",
            f"ELINT: {selected_target.elint_signature}MHz",
            f"THREAT: {selected_target.threat_level}"
        ]
        pygame.draw.rect(screen, FRAME_GRAY, (WIDTH - int(HUD_WIDTH * 0.6), 150, int(HUD_WIDTH * 0.58), 600), border_radius=10)
        for i, line in enumerate(info):
            text = font.render(line, True, WHITE if i < 12 else PURPLE if i == 13 else ORANGE)
            screen.blit(text, (WIDTH - int(HUD_WIDTH * 0.6) + 20, 160 + i * 35))

    # Altitude graph
    if selected_target:
        altitude_graph.fill((BG_DARK[0], BG_DARK[1], BG_DARK[2], 220))
        pygame.draw.rect(altitude_graph, FRAME_GRAY, (0, 0, ALT_GRAPH_SIZE[0], ALT_GRAPH_SIZE[1]), 2)
        for i in range(1, len(selected_target.alt_history)):
            x1 = (i - 1) * ALT_GRAPH_SIZE[0] // 50
            x2 = i * ALT_GRAPH_SIZE[0] // 50
            y1 = ALT_GRAPH_SIZE[1] - (selected_target.alt_history[i - 1] / 50000) * (ALT_GRAPH_SIZE[1] - 10)
            y2 = ALT_GRAPH_SIZE[1] - (selected_target.alt_history[i] / 50000) * (ALT_GRAPH_SIZE[1] - 10)
            pygame.draw.line(altitude_graph, ACCENT_BLUE, (x1, y1), (x2, y2), 2)
        text = small_font.render("ALTITUDE (ft)", True, WHITE)
        screen.blit(altitude_graph, (WIDTH - int(HUD_WIDTH * 0.6), HEIGHT - ALT_GRAPH_SIZE[1] - LOG_HEIGHT - 50))
        screen.blit(text, (WIDTH - int(HUD_WIDTH * 0.6), HEIGHT - ALT_GRAPH_SIZE[1] - LOG_HEIGHT - 70))

    # Command log
    command_log.fill((BG_DARK[0], BG_DARK[1], BG_DARK[2], 220))
    pygame.draw.rect(command_log, FRAME_GRAY, (0, 0, HUD_WIDTH - 20, LOG_HEIGHT), 2)
    log_entries = log_entries[-int(LOG_HEIGHT / 20):]  # Limit to visible lines
    for i, entry in enumerate(log_entries):
        text = small_font.render(entry, True, WHITE)
        screen.blit(command_log, (WIDTH - HUD_WIDTH + 10, HEIGHT - LOG_HEIGHT - 20))
        screen.blit(text, (WIDTH - HUD_WIDTH + 20, HEIGHT - LOG_HEIGHT - 10 + i * 20))

    # Status bar
    status = font.render(f"SYS: ONLINE | DATE: 23 FEB 2025 | POS: 35.7N 139.7E | ALT: 35000ft | MODE: {radar_mode}", True, ACCENT_BLUE)
    pygame.draw.rect(screen, FRAME_GRAY, (0, HEIGHT - 60, WIDTH, 60))
    screen.blit(status, (20, HEIGHT - 45))

    # Lock warning
    if lock_warning:
        warning = font.render("WARNING: THREAT LOCK DETECTED", True, ORANGE)
        pygame.draw.rect(screen, (BG_DARK[0], BG_DARK[1], BG_DARK[2], 220), (WIDTH // 2 - 250, 50, 500, 80), border_radius=10)
        pygame.draw.rect(screen, ORANGE, (WIDTH // 2 - 250, 50, 500, 80), 2, border_radius=10)
        screen.blit(warning, (WIDTH // 2 - 230, 75))

    # ELINT overlay
    if elint_active:
        for target in targets:
            if pygame.time.get_ticks() - target.last_sweep < 6000:
                x = RADAR_CENTER[0] + target.distance * math.cos(math.radians(target.angle)) * zoom_level
                y = RADAR_CENTER[1] - target.distance * math.sin(math.radians(target.angle)) * zoom_level
                text = small_font.render(f"{target.elint_signature}", True, PURPLE)
                screen.blit(text, (int(x) + 30, int(y) + 10))

    # Update display
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
