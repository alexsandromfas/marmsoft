"""Helper screens for menu prompts and game over display."""

import pygame
from FlyBird.modules.settings import *
from FlyBird.modules.utils import *

class Screens:
    """Collection of simple UI screens used by :class:`Game`."""

    def __init__(self, game):
        """Store references to the main :class:`Game` object."""
        self.game = game
        self.screen = game.screen
        self.clock = game.clock
        self.font = game.font

    def show_start_screen(self):
        """Display the initial title and wait for ENTER."""
        self.screen.fill(BLACK)
        font_large = pygame.font.Font(None, 72)
        title_text = font_large.render("FlyBird", True, WHITE)
        self.screen.blit(title_text, (WIDTH // 2 - title_text.get_width() // 2, HEIGHT // 3))

        font_small = pygame.font.Font(None, 36)
        instruction_text = font_small.render("Pressione ENTER para iniciar", True, WHITE)
        self.screen.blit(instruction_text, (WIDTH // 2 - instruction_text.get_width() // 2, HEIGHT // 2))

        pygame.display.flip()

        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    self.game.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        waiting = False



    def show_go_screen(self):
        """Display score information and allow the player to choose an action."""
        # Calculate score and amplitudes
        obstacles_passed = self.game.bird.obstacles_passed
        if self.game.bird.amplitudes:
            total_phalange1 = max(a[0] for a in self.game.bird.amplitudes) - min(a[0] for a in self.game.bird.amplitudes)
            total_phalange2 = max(a[1] for a in self.game.bird.amplitudes) - min(a[1] for a in self.game.bird.amplitudes)
        else:
            total_phalange1 = total_phalange2 = 0

        # Game Over screen
        self.screen.fill(BLACK)
        self.game.save_results
        font_large = pygame.font.Font(None, 72)
        game_over_text = font_large.render("GAME OVER", True, WHITE)
        self.screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 6))

        font_small = pygame.font.Font(None, 36)
        # Display score
        score_text = font_small.render(f"Obstáculos ultrapassados: {obstacles_passed}", True, WHITE)
        amplitude_text = font_small.render(
            f"Amplitude Falange 1: {total_phalange1:.2f}°   Amplitude Falange 2: {total_phalange2:.2f}°", True, WHITE)
        self.screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 6 + 80))
        self.screen.blit(amplitude_text, (WIDTH // 2 - amplitude_text.get_width() // 2, HEIGHT // 6 + 120))

        # Buttons
        buttons = []
        button_texts = ["Jogar Novamente", "Trocar Paciente", "Sair"]
        button_actions = [self.game.play_again, self.game.change_patient, self.game.quit_game]
        button_width = 200
        button_height = 50
        button_margin = 20
        total_height = len(button_texts) * (button_height + button_margin) - button_margin
        start_y = HEIGHT // 2

        for i, text in enumerate(button_texts):
            rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + i * (button_height + button_margin), button_width, button_height)
            buttons.append((rect, text, button_actions[i]))

        waiting = True
        while waiting:
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    waiting = False
                    self.game.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    for rect, text, action in buttons:
                        if rect.collidepoint(mouse_pos):
                            action()
                            waiting = False
                            break

            # Redraw the screen elements
            self.screen.fill(BLACK)
            self.screen.blit(game_over_text, (WIDTH // 2 - game_over_text.get_width() // 2, HEIGHT // 6))
            self.screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 6 + 80))
            self.screen.blit(amplitude_text, (WIDTH // 2 - amplitude_text.get_width() // 2, HEIGHT // 6 + 120))

            for rect, text, _ in buttons:
                pygame.draw.rect(self.screen, WHITE, rect)
                button_text = font_small.render(text, True, BLACK)
                text_rect = button_text.get_rect(center=rect.center)
                self.screen.blit(button_text, text_rect)

            pygame.display.flip()

    
    def get_player_name(self):
        """Prompt the player to enter their name."""
        font_small = pygame.font.Font(None, 36)
        name_prompt = font_small.render("Digite seu nome:", True, WHITE)
        input_box = pygame.Rect(WIDTH // 2 - 150, HEIGHT // 2 - 20, 300, 40)
        name_text = ''
        active = True
        cursor_visible = True
        cursor_timer = 0
        cursor_interval = 500  # milliseconds

        # Next button
        next_button = pygame.Rect(WIDTH // 2 - 50, input_box.bottom + 20, 100, 40)
        next_button_text = font_small.render("Próximo", True, BLACK)

        while active:
            current_time = pygame.time.get_ticks()
            if current_time - cursor_timer > cursor_interval:
                cursor_visible = not cursor_visible
                cursor_timer = current_time

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    active = False
                    self.game.running = False
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        if name_text.strip() != '':
                            active = False
                            self.game.player_name = name_text
                            return
                    elif event.key == pygame.K_BACKSPACE:
                        name_text = name_text[:-1]
                    else:
                        name_text += event.unicode
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    if next_button.collidepoint(mouse_pos):
                        if name_text.strip() != '':
                            active = False
                            self.game.player_name = name_text
                            return

            self.screen.fill(BLACK)
            self.screen.blit(name_prompt, (WIDTH // 2 - name_prompt.get_width() // 2, HEIGHT // 2 - 80))
            pygame.draw.rect(self.screen, WHITE, input_box, 2)
            name_surface = font_small.render(name_text, True, WHITE)
            self.screen.blit(name_surface, (input_box.x + 5, input_box.y + 5))

            # Blinking cursor
            if cursor_visible:
                cursor_rect = pygame.Rect(input_box.x + 5 + name_surface.get_width(), input_box.y + 5, 2, name_surface.get_height())
                pygame.draw.rect(self.screen, WHITE, cursor_rect)

            # Draw Next button
            pygame.draw.rect(self.screen, WHITE, next_button)
            text_rect = next_button_text.get_rect(center=next_button.center)
            self.screen.blit(next_button_text, text_rect)

            pygame.display.flip()
            self.clock.tick(30)


    def get_finger_choice(self):
        """Let the player choose which finger to exercise."""
        font_small = pygame.font.Font(None, 36)
        finger_prompt = font_small.render("Escolha o dedo para exercitar:", True, WHITE)

        # Define finger buttons
        fingers = ['Polegar', 'Indicador', 'Médio', 'Anelar', 'Mínimo']
        finger_buttons = []
        button_width = 200
        button_height = 50
        button_margin = 10
        total_height = len(fingers) * (button_height + button_margin) - button_margin
        start_y = HEIGHT // 2 - total_height // 2 + 50

        for i, finger in enumerate(fingers):
            rect = pygame.Rect(WIDTH // 2 - button_width // 2, start_y + i * (button_height + button_margin), button_width, button_height)
            finger_buttons.append((rect, finger))

        active = True
        while active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    active = False
                    self.game.running = False
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = event.pos
                    for rect, finger in finger_buttons:
                        if rect.collidepoint(mouse_pos):
                            self.game.selected_finger = finger.lower()
                            active = False
                            return

            self.screen.fill(BLACK)
            # Draw finger prompt
            self.screen.blit(finger_prompt, (WIDTH // 2 - finger_prompt.get_width() // 2, HEIGHT // 6))

            # Draw finger buttons
            for rect, finger in finger_buttons:
                pygame.draw.rect(self.screen, WHITE, rect)
                finger_text = font_small.render(finger, True, BLACK)
                text_rect = finger_text.get_rect(center=rect.center)
                self.screen.blit(finger_text, text_rect)

            pygame.display.flip()
            self.clock.tick(30)

