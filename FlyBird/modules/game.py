"""Arcade style game controlled by flex sensor input."""

import pygame
import random
import csv
import os
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
        self.cloud_images = load_images_from_folder(NUVENS_DIR)
        self.wood_images = load_images_from_folder(WOOD_DIR)
        bird_frames = load_images_from_folder(BIRD_DIR, scale_factor=BIRD_SCALE, remove_bg=True, base_color=(0, 255, 0))
        self.bird = Bird(bird_frames)
        self.bird = Bird(bird_frames, sensor_data_provider=self.sensor_data_provider)


        # Load obstacles from CSV
        self.woods = pygame.sprite.Group()
        obstacles = load_obstacles_from_csv()
        for obstacle_data in obstacles:
            wood = Wood(obstacle_data["image"], obstacle_data["x"], obstacle_data["y"], obstacle_data["bottom"])
            self.woods.add(wood)

        # Generate initial clouds
        self.clouds = pygame.sprite.Group()
        for cloud_data in generate_clouds(self.cloud_images):
            cloud = Cloud(cloud_data["image"], cloud_data["x"], cloud_data["y"], cloud_data["speed"])
            self.clouds.add(cloud)


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
        self.bird.update(keys_pressed)
        self.bird.check_invincibility()
        self.clouds.update()
        self.woods.update()

        # Check collisions
        if not self.bird.is_invincible:
            bird_mask = pygame.mask.from_surface(self.bird.image)
            for wood in self.woods:
                wood_mask = pygame.mask.from_surface(wood.image)
                offset = (int(wood.rect.x - self.bird.rect.x), int(wood.rect.y - self.bird.rect.y))
                if bird_mask.overlap(wood_mask, offset):
                    print("Collision!")
                    self.bird.handle_collision()
                    if self.bird.lives <= 0:
                        print("Game Over!")
                        print(f"Total obstacles passed: {self.bird.obstacles_passed}")
                        self.game_over = True

        # Check if bird has passed any woods
        for wood in self.woods:
            if not wood.passed and wood.rect.right < self.bird.rect.left:
                wood.passed = True
                self.bird.pass_obstacle()



    def draw(self):
        """Render all game elements to the screen."""
        self.screen.blit(self.background, (0, 0))
        self.clouds.draw(self.screen)
        self.bird.draw(self.screen)
        self.woods.draw(self.screen)

        # Draw lives
        lives_text = self.font.render(f"Vidas: {self.bird.lives}", True, WHITE)
        self.screen.blit(lives_text, (WIDTH - 150, 20))

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

        # Reload clouds
        self.clouds.empty()
        for cloud_data in generate_clouds(self.cloud_images):
            cloud = Cloud(cloud_data["image"], cloud_data["x"], cloud_data["y"], cloud_data["speed"])
            self.clouds.add(cloud)

        # Reload woods from CSV
        self.woods.empty()
        obstacles = load_obstacles_from_csv()
        for obstacle_data in obstacles:
            wood = Wood(obstacle_data["image"], obstacle_data["x"], obstacle_data["y"], obstacle_data["bottom"])
            self.woods.add(wood)

    
    def save_results(self):
        """Append the player's session results to ``results.csv``."""
        # Save player's performance to CSV
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        file_exists = os.path.isfile(RESULTS_FILE)
        with open(RESULTS_FILE, 'a', newline='') as csvfile:
            fieldnames = ['Nome', 'Dedo', 'Obstáculos Ultrapassados', 'Amplitude Falange 1', 'Amplitude Falange 2']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            # Compute total amplitudes
            if self.bird.amplitudes:
                total_phalange1 = max(a[0] for a in self.bird.amplitudes) - min(a[0] for a in self.bird.amplitudes)
                total_phalange2 = max(a[1] for a in self.bird.amplitudes) - min(a[1] for a in self.bird.amplitudes)
            else:
                total_phalange1 = total_phalange2 = 0
            writer.writerow({
                'Nome': self.player_name,
                'Dedo': self.selected_finger,
                'Obstáculos Ultrapassados': self.bird.obstacles_passed,
                'Amplitude Falange 1': f"{total_phalange1:.2f}",
                'Amplitude Falange 2': f"{total_phalange2:.2f}"
            })
        # Confirmation message in terminal
        print("Resultados Salvos!")

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
