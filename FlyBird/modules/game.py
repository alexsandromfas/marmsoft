"""Arcade style game controlled by flex sensor input."""

import pygame
import random
import csv
import os
import json
from FlyBird.modules.sprites import Bird, Wood, Cloud
from FlyBird.modules.settings import *
from FlyBird.modules.utils import *
from FlyBird.modules.input_handler import get_input
from FlyBird.modules.screens import Screens

class Game:
    """Main game class handling state, events and rendering."""

    def __init__(self, sensor_data_provider=None):
        """Initialize pygame and load assets.

        Parameters
        ----------
        sensor_data_provider : Callable[[], float], optional
            Function returning the current flex sensor angle.
        """
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("FlyBird")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.font = pygame.font.Font(None, 36)
        self.sensor_data_provider = sensor_data_provider  # Mova esta linha antes de load_data()
        # Calibration values (set via calibration screen)
        self.calib_ext_min = None
        self.calib_flex_max = None
        # Infinite obstacle spawning control (must be set before load_data pre-seed)
        self._wood_spawn_distance = random.randint(280, 420)
        self._wood_speed_px = 3  # must match Wood.update speed
        self._next_is_bottom = bool(random.getrandbits(1))
        self._last_wood_image_idx = None  # avoid immediate image repetition

        # Speed ramp control
        self.speed_ramp_enabled = getattr(self, 'speed_ramp_enabled', False)
        self.speed_factor = 1.0
        self._speed_start_ms = pygame.time.get_ticks()
        self._speed_ramp_per_sec = 0.015  # increase 1.5% per second (tunable)
        self._speed_cap = 2.5  # do not exceed 2.5x by default
        self.max_speed_factor = 1.0

        self.load_data()
        self.player_name = ""
        self.selected_finger = ""
        self.screens = Screens(self)
        self.started = False  # Use this flag if necessary
        print("Game initialized.")



    def load_data(self):
        """Load images and obstacle data from disk."""
        # Load images
        self.background = pygame.image.load(os.path.join(ASSETS_DIR, "Background", "background.png")).convert()
        self._bg_scaled = None
        self._bg_scaled_size = None
        self.cloud_images = load_images_from_folder(NUVENS_DIR)
        self.wood_images = load_images_from_folder(WOOD_DIR)
        bird_frames = load_images_from_folder(BIRD_DIR, scale_factor=BIRD_SCALE, remove_bg=True, base_color=(0, 255, 0))
        self.bird = Bird(bird_frames)
        self.bird = Bird(bird_frames, sensor_data_provider=self.sensor_data_provider)

        # Woods group (infinite spawning, not from CSV anymore)
        self.woods = pygame.sprite.Group()

        # Generate initial clouds
        self.clouds = pygame.sprite.Group()
        for cloud_data in generate_clouds(self.cloud_images):
            cloud = Cloud(cloud_data["image"], cloud_data["x"], cloud_data["y"], cloud_data["speed"])
            self.clouds.add(cloud)

        # Pre-seed a few woods off-screen to the right with generous spacing
        last_right = WIDTH
        for _ in range(3):
            spacing = random.randint(480, 700)
            x = max(WIDTH + 80, last_right + spacing)
            self._spawn_wood(x_override=x)
            # Update last_right using the spawned wood's width (approximate)
            last_right = x + 200

    def _spawn_wood(self, x_override: int | None = None):
        """Spawn one wood obstacle, alternating top/bottom, with difficulty-safe scale and spacing."""
        if not self.wood_images:
            return
        # Choose image avoiding immediate repetition when possible
        if len(self.wood_images) > 1:
            idx = random.randrange(len(self.wood_images))
            if self._last_wood_image_idx is not None and idx == self._last_wood_image_idx:
                idx = (idx + 1) % len(self.wood_images)
            self._last_wood_image_idx = idx
            base_img = self.wood_images[idx]
        else:
            base_img = self.wood_images[0]
        # Vary scale to alter difficulty but keep passable gap
        scale = random.uniform(0.35, 0.6)
        img = pygame.transform.scale(
            base_img,
            (int(base_img.get_width() * scale), int(base_img.get_height() * scale))
        )
        # Orientation alternating: bottom, then top, etc.
        bottom = self._next_is_bottom
        self._next_is_bottom = not self._next_is_bottom

        # Difficulty factor d in [0,1]: higher means harder (more of the trunk visible inside screen)
        # Bias some obstacles to be almost fully visible (harder)
        if random.random() < 0.35:
            d = random.uniform(0.85, 1.0)
        else:
            d = random.uniform(0.45, 0.95)
        # Visible penetration inside the screen, clamp to reasonable bounds
        min_pen = 60
        min_free_space = 150  # ensure at least this much free screen area
        max_pen = min( HEIGHT - min_free_space, img.get_height() - 20 )
        if max_pen < min_pen:
            max_pen = min_pen
        penetration = int(min_pen + d * (max_pen - min_pen))

        # Ensure passable free space by capping trunk height proportionally
        max_allowed_h = max(50, HEIGHT - min_free_space)
        if img.get_height() > max_allowed_h:
            new_h = max_allowed_h
            new_w = int(img.get_width() * (new_h / img.get_height()))
            img = pygame.transform.smoothscale(img, (new_w, new_h))
            # adjust penetration within new bounds
            max_pen = min( HEIGHT - min_free_space, img.get_height() - 20 )
            penetration = min(max(penetration, min_pen), max_pen)

        # Compute y so the trunk is partially outside the screen
        if bottom:
            # visible portion from bottom = penetration; so y = HEIGHT - penetration
            y = HEIGHT - penetration
        else:
            # top trunk: flip and position so only 'penetration' pixels are visible
            img = pygame.transform.flip(img, False, True)
            y = - (img.get_height() - penetration)

        # Compute x based on last rightmost obstacle to prevent overlap and closeness
        if x_override is not None:
            x = x_override
        else:
            last_right = max((w.rect.right for w in self.woods), default=WIDTH)
            spacing = random.randint(360, 600)
            x = max(WIDTH + 80, last_right + spacing)
        wood = Wood(img, x, y, bottom)
        self.woods.add(wood)


    def new(self):
        """Reset game state for a new round."""
        self.reset()  # Reset game variables
        print("New game started.")


    def run(self):
        """Main game loop."""
        while self.running and not self.game_over:
            self.clock.tick(FPS)
            self.events()
            self.update()
            self.draw()

    def events(self):
        """Process pending pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

    def update(self):
        """Update sprites and check for collisions."""
        keys_pressed = pygame.key.get_pressed()

        # Update speed factor smoothly over time
        if self.speed_ramp_enabled:
            elapsed_s = max(0.0, (pygame.time.get_ticks() - self._speed_start_ms) / 1000.0)
            self.speed_factor = min(self._speed_cap, 1.0 + elapsed_s * self._speed_ramp_per_sec)
        else:
            self.speed_factor = 1.0
        if self.speed_factor > self.max_speed_factor:
            self.max_speed_factor = self.speed_factor
        # Adjust bird flap animation rate with speed factor (faster flaps)
        base_rate = BIRD_FRAME_RATE
        min_ms = 40
        self.bird.frame_rate = max(min_ms, int(base_rate / self.speed_factor))
        self.bird.update(keys_pressed)
        self.bird.check_invincibility()
        # Scale cloud and wood speeds before updating
        for cloud in self.clouds:
            cloud.speed = cloud.base_speed * self.speed_factor
        for wood in self.woods:
            wood.speed = 3.0 * self.speed_factor
        self.clouds.update()
        self.woods.update()

        # Spawn new woods when countdown elapses; ensure final x respects last-right spacing
        # Spawn countdown scales with speed (more speed -> spawns sooner)
        self._wood_spawn_distance -= (self._wood_speed_px * self.speed_factor)
        if self._wood_spawn_distance <= 0:
            last_right = max((w.rect.right for w in self.woods), default=WIDTH)
            # Slightly reduce spacing as speed grows to keep rhythm, but not too tight
            base_min, base_max = 380, 620
            shrink = int((self.speed_factor - 1.0) * 80)  # shrink up to ~120px near cap
            spacing = random.randint(max(300, base_min - shrink), max(420, base_max - shrink))
            x = max(WIDTH + 80, last_right + spacing)
            self._spawn_wood(x_override=x)
            # Reset distance a bit smaller at higher speeds
            base_min_d, base_max_d = 220, 360
            dist_shrink = int((self.speed_factor - 1.0) * 40)
            self._wood_spawn_distance = random.randint(max(160, base_min_d - dist_shrink), max(260, base_max_d - dist_shrink))

        # Check collisions (rect first, then mask using cached masks)
        if not self.bird.is_invincible:
            bird_mask = self.bird.get_mask()
            for wood in self.woods:
                if self.bird.rect.colliderect(wood.rect):
                    if wood.mask is None or bird_mask is None:
                        continue
                    offset = (int(wood.rect.x - self.bird.rect.x), int(wood.rect.y - self.bird.rect.y))
                    if bird_mask.overlap(wood.mask, offset):
                        self.bird.handle_collision()
                        if self.bird.lives <= 0:
                            self.game_over = True

        # Check if bird has passed any woods
        for wood in self.woods:
            if not wood.passed and wood.rect.right < self.bird.rect.left:
                wood.passed = True
                self.bird.pass_obstacle()



    def draw(self):
        """Render all game elements to the screen."""
        # Scale background to current window size (cache the scaled surface)
        w, h = self.screen.get_size()
        if self._bg_scaled is None or self._bg_scaled_size != (w, h):
            if self.background.get_width() != w or self.background.get_height() != h:
                self._bg_scaled = pygame.transform.smoothscale(self.background, (w, h))
            else:
                self._bg_scaled = self.background
            self._bg_scaled_size = (w, h)
        self.screen.blit(self._bg_scaled, (0, 0))
        self.clouds.draw(self.screen)
        self.bird.draw(self.screen)
        self.woods.draw(self.screen)

        # Draw lives
        lives_text = self.font.render(f"Vidas: {self.bird.lives}", True, WHITE)
        self.screen.blit(lives_text, (w - 150, 20))

        pygame.display.flip()


    
    
    def get_player_info(self, new_player=True):
        """Prompt for the player's name and finger."""
        self.screen.fill(BLACK)
        font_small = pygame.font.Font(None, 36)
        name_prompt = font_small.render("Digite seu nome:", True, WHITE)
        finger_prompt = font_small.render("Escolha o dedo para exercitar:", True, WHITE)

        input_box = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 - 20, 200, 40)
        name_text = self.player_name if not new_player else ''
        active_name = new_player
        cursor_visible = True
        cursor_timer = 0
        cursor_interval = 500  # milliseconds

        # Define finger buttons
        fingers = ['Polegar', 'Indicador', 'Médio', 'Anelar', 'Mínimo']
        finger_buttons = []
        button_width = 150
        button_height = 40
        button_margin = 10
        total_height = len(fingers) * (button_height + button_margin) - button_margin
        start_y = HEIGHT // 2 - total_height // 2 + 100

        for i, finger in enumerate(fingers):
            rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + i * (button_height + button_margin), button_width, button_height)
            finger_buttons.append((rect, finger))

        # Next button
        next_button = pygame.Rect(WIDTH // 2 - 50, input_box.bottom + 20, 100, 40)
        next_button_text = font_small.render("Próximo", True, BLACK)

        while True:
            current_time = pygame.time.get_ticks()
            if current_time - cursor_timer > cursor_interval:
                cursor_visible = not cursor_visible
                cursor_timer = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                if event.type == pygame.KEYDOWN and active_name:
                    if event.key == pygame.K_RETURN:
                        if name_text.strip() != '':
                            active_name = False
                    elif event.key == pygame.K_BACKSPACE:
                        name_text = name_text[:-1]
                    else:
                        name_text += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    if active_name:
                        if input_box.collidepoint(mouse_pos):
                            active_name = True
                        elif next_button.collidepoint(mouse_pos):
                            if name_text.strip() != '':
                                active_name = False
                    elif not active_name:
                        for rect, finger in finger_buttons:
                            if rect.collidepoint(mouse_pos):
                                self.player_name = name_text
                                self.selected_finger = finger.lower()
                                return

            self.screen.fill(BLACK)
            # Draw name prompt and input box
            self.screen.blit(name_prompt, (WIDTH // 2 - name_prompt.get_width() // 2, HEIGHT // 2 - 80))
            pygame.draw.rect(self.screen, WHITE, input_box, 2)
            name_surface = font_small.render(name_text, True, WHITE)
            self.screen.blit(name_surface, (input_box.x + 5, input_box.y + 5))

            # Blinking cursor
            if active_name and cursor_visible:
                cursor_rect = pygame.Rect(input_box.x + 5 + name_surface.get_width(), input_box.y + 5, 2, name_surface.get_height())
                pygame.draw.rect(self.screen, WHITE, cursor_rect)

            # Draw Next button
            if active_name:
                pygame.draw.rect(self.screen, WHITE, next_button)
                text_rect = next_button_text.get_rect(center=next_button.center)
                self.screen.blit(next_button_text, text_rect)
            else:
                # Draw finger prompt
                self.screen.blit(finger_prompt, (WIDTH // 2 - finger_prompt.get_width() // 2, HEIGHT // 2 - 150))
                # Draw finger buttons
                for rect, finger in finger_buttons:
                    pygame.draw.rect(self.screen, WHITE, rect)
                    finger_text = font_small.render(finger, True, BLACK)
                    text_rect = finger_text.get_rect(center=rect.center)
                    self.screen.blit(finger_text, text_rect)

            pygame.display.flip()
            self.clock.tick(30)


    def reset(self):
        """Reset sprites and reload obstacles."""
        self.game_over = False
        self.bird.lives = INITIAL_LIVES
        self.bird.rect.center = (WIDTH // 2 - 50, HEIGHT // 2)
        self.bird.velocity = 0
        self.bird.amplitudes.clear()
        self.bird.obstacles_passed = 0
        # Reset speed ramp tracking for a new run
        self.max_speed_factor = 1.0
        self._speed_start_ms = pygame.time.get_ticks()

        # Reload clouds
        self.clouds.empty()
        for cloud_data in generate_clouds(self.cloud_images):
            cloud = Cloud(cloud_data["image"], cloud_data["x"], cloud_data["y"], cloud_data["speed"])
            self.clouds.add(cloud)

        # Reset woods and re-seed a few to the right
        self.woods.empty()
        self._wood_spawn_distance = random.randint(220, 360)
        self._next_is_bottom = bool(random.getrandbits(1))
        last_right = WIDTH
        for _ in range(3):
            spacing = random.randint(380, 560)
            x = max(WIDTH + 80, last_right + spacing)
            self._spawn_wood(x_override=x)
            last_right = x + 200

    
    def save_results(self):
        """Persist the player's session results to JSON (preferred) and optionally CSV."""
        from FlyBird.modules.settings import RESULTS_JSON
        # Ensure data folder exists
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)

        # Compute observed amplitude if available from sensor
        if (self.bird.obs_angle_min is not None) and (self.bird.obs_angle_max is not None):
            amplitude_max = self.bird.obs_angle_max - self.bird.obs_angle_min
            ang_min = self.bird.obs_angle_min
            ang_max = self.bird.obs_angle_max
        else:
            if self.bird.amplitudes:
                series = [a[0] for a in self.bird.amplitudes]
                ang_min = min(series)
                ang_max = max(series)
                amplitude_max = ang_max - ang_min
            else:
                ang_min = ang_max = amplitude_max = 0.0

        rec = {
            'Nome': self.player_name or '',
            'Articulacao': self.selected_finger or '',
            'AnguloFlexMax': round(float(ang_max), 2) if isinstance(ang_max, (int, float)) else 0.0,
            'AnguloExtMin': round(float(ang_min), 2) if isinstance(ang_min, (int, float)) else 0.0,
            'AmplitudeMax': round(float(amplitude_max), 2) if isinstance(amplitude_max, (int, float)) else 0.0,
            'Obstaculos': int(self.bird.obstacles_passed),
            'VelocidadeMax': round(float(self.max_speed_factor), 2)
        }

        # Write to JSON (canonical source for leaderboard)
        data = []
        if os.path.isfile(RESULTS_JSON):
            try:
                with open(RESULTS_JSON, 'r', encoding='utf-8') as f:
                    data = json.load(f) or []
                if not isinstance(data, list):
                    data = []
            except Exception:
                data = []
        data.append(rec)
        try:
            with open(RESULTS_JSON, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            # As a safety net, do not crash the game if disk write fails
            pass

        # Optional: still append CSV for legacy reference (not used for leaderboard anymore)
        try:
            file_exists = os.path.isfile(RESULTS_FILE)
            with open(RESULTS_FILE, 'a', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'Nome','Articulacao','AnguloFlexMax','AnguloExtMin','AmplitudeMax','Obstaculos','VelocidadeMax'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists or os.path.getsize(RESULTS_FILE) == 0:
                    writer.writeheader()
                writer.writerow({
                    'Nome': rec['Nome'],
                    'Articulacao': rec['Articulacao'],
                    'AnguloFlexMax': f"{rec['AnguloFlexMax']:.2f}",
                    'AnguloExtMin': f"{rec['AnguloExtMin']:.2f}",
                    'AmplitudeMax': f"{rec['AmplitudeMax']:.2f}",
                    'Obstaculos': rec['Obstaculos'],
                    'VelocidadeMax': f"{rec['VelocidadeMax']:.2f}"
                })
        except Exception:
            pass

        print("Resultados salvos (JSON).")

    def play_again(self):
        """Start a new game using the same player."""
        self.reset()
        self.screens.get_finger_choice()
        if self.running:
            self.game_over = False  # Ensure game_over is reset


    def change_patient(self):
        """Reset game data and prompt for a new player."""
        self.reset()
        self.player_name = ''
        self.selected_finger = ''
        self.screens.get_player_name()
        if self.running:
            self.screens.get_finger_choice()
        if self.running:
            # Calibrate again for the new patient
            self.screens.calibrate_range()
        if self.running:
            self.game_over = False  # Ensure game_over is reset




    def quit_game(self):
        """Exit the game loop."""
        self.running = False
        try:
            # Encerra subsistemas do pygame para permitir reabrir o jogo depois
            import pygame as _pg
            _pg.quit()
        except Exception:
            pass
