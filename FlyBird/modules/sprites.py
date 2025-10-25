"""Sprite classes for the FlyBird game."""

import pygame
import random
from FlyBird.modules.settings import *
from FlyBird.modules.utils import remove_background_with_tolerance

class Bird(pygame.sprite.Sprite):
    """Player controlled bird sprite."""

    def __init__(self, frames, sensor_data_provider=None):
        """Create the bird.

        Parameters
        ----------
        frames : list[Surface]
            Animation frames for the bird.
        sensor_data_provider : Callable[[], float], optional
            Function returning the current flex sensor angle.
        """
        super().__init__()
        self.frames = frames
        self.index = 0
        self.image = self.frames[self.index]
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH // 2 - 50, HEIGHT // 2)
        self.velocity = 0
        self.acceleration = BIRD_ACCELERATION
        self.max_speed = BIRD_MAX_SPEED
        self.friction = BIRD_FRICTION
        self.last_update = pygame.time.get_ticks()
        self.frame_rate = BIRD_FRAME_RATE
        self.is_invincible = False
        self.invincible_start_time = 0
        self.lives = INITIAL_LIVES
        self.amplitudes = []  # Store tuples of (phalange1, phalange2)
        self.obstacles_passed = 0  # New attribute to track obstacles passed
        self.sensor_data_provider = sensor_data_provider

        # Calibration limits (extension = lower angle -> top; flexion = higher angle -> bottom)
        self.calib_ext_min = None  # menor ângulo (topo)
        self.calib_flex_max = None  # maior ângulo (base)

        # Simulate amplitudes based on bird's initial vertical position
        position_ratio = self.rect.y / (HEIGHT - self.image.get_height())
        angle = position_ratio * (FLEX_SENSOR_MAX - FLEX_SENSOR_MIN) + FLEX_SENSOR_MIN
        self.amplitudes.append((angle, angle))
    def update(self, keys_pressed):
        """Update the bird position and animation."""
        current_time = pygame.time.get_ticks()
        if current_time - self.last_update > self.frame_rate:
            self.index = (self.index + 1) % len(self.frames)
            self.image = self.frames[self.index]
            self.last_update = current_time

        # Update amplitudes (simulate or use actual sensor data)
        if self.sensor_data_provider is not None:
            current_angle = self.sensor_data_provider()
            if current_angle is None:
                current_angle = SENSOR_ANGLE_MIN  # fallback

            # Use calibrated limits if available; otherwise fallback to global sensor range
            ext_min = self.calib_ext_min if self.calib_ext_min is not None else SENSOR_ANGLE_MIN
            flex_max = self.calib_flex_max if self.calib_flex_max is not None else SENSOR_ANGLE_MAX

            # Avoid division by zero
            if flex_max == ext_min:
                position_ratio = 0.5
            else:
                # Map: extension (lower angle) -> top (0), flexion (higher) -> bottom (1)
                position_ratio = (current_angle - ext_min) / (flex_max - ext_min)
                position_ratio = max(0.0, min(1.0, position_ratio))

            target_y = position_ratio * (HEIGHT - self.image.get_height())

            # Smooth movement towards target_y
            smoothing_factor = 0.1  # 0..1
            self.rect.y += (target_y - self.rect.y) * smoothing_factor

            # Keep within bounds
            self.rect.y = max(-10, min(self.rect.y, HEIGHT - self.image.get_height()))
        else:
            # Controle via teclado (caso o sensor não esteja disponível)
            if keys_pressed[pygame.K_UP]:
                self.rect.y -= self.max_speed
            elif keys_pressed[pygame.K_DOWN]:
                self.rect.y += self.max_speed
            # Garantir que o pássaro permaneça dentro dos limites da tela
            self.rect.y = max(0, min(self.rect.y, HEIGHT - self.image.get_height()))

        # Atualizar amplitudes com base na nova posição
        position_ratio = self.rect.y / (HEIGHT - self.image.get_height())
        angle = position_ratio * (FLEX_SENSOR_MAX - FLEX_SENSOR_MIN) + FLEX_SENSOR_MIN
        self.amplitudes.append((angle, angle))
        
    # def update(self, keys_pressed):
    #     current_time = pygame.time.get_ticks()
    #     if current_time - self.last_update > self.frame_rate:
    #         self.index = (self.index + 1) % len(self.frames)
    #         self.image = self.frames[self.index]
    #         self.last_update = current_time

    #     # Update amplitudes (simulate or use actual sensor data)
    #     if self.sensor_data_provider is not None:
    #         current_angle = self.sensor_data_provider()
    #         if SENSOR_ANGLE_MIN <= current_angle <= SENSOR_ANGLE_MAX:
    #             position_ratio = (current_angle - SENSOR_ANGLE_MIN) / (SENSOR_ANGLE_MAX - SENSOR_ANGLE_MIN)
    #             target_y = position_ratio * (HEIGHT - self.image.get_height())
    #             delta_y = target_y - self.rect.y

    #             # Update velocity towards target position
    #             self.velocity += delta_y * self.acceleration

    #             # Apply friction
    #             if self.velocity > 0:
    #                 self.velocity -= self.friction
    #             elif self.velocity < 0:
    #                 self.velocity += self.friction

    #             # Limit max speed
    #             self.velocity = max(-self.max_speed, min(self.velocity, self.max_speed))

    #             # Update position
    #             self.rect.y += self.velocity
    #             # Ensure bird stays within screen bounds
    #             self.rect.y = max(0, min(self.rect.y, HEIGHT - self.image.get_height()))
    #         else:
    #             # Gradually slow down the bird
    #             if self.velocity > 0:
    #                 self.velocity -= self.friction
    #             elif self.velocity < 0:
    #                 self.velocity += self.friction
    #             self.rect.y += self.velocity
    #             self.rect.y = max(0, min(self.rect.y, HEIGHT - self.image.get_height()))
    #     else:
    #         # Fallback to keyboard controls
    #         if keys_pressed[pygame.K_UP]:
    #             self.velocity -= self.acceleration
    #         elif keys_pressed[pygame.K_DOWN]:
    #             self.velocity += self.acceleration
    #         else:
    #             if self.velocity > 0:
    #                 self.velocity -= self.friction
    #             elif self.velocity < 0:
    #                 self.velocity += self.friction
    #         self.velocity = max(-self.max_speed, min(self.velocity, self.max_speed))
    #         self.rect.y += self.velocity
    #         self.rect.y = max(0, min(self.rect.y, HEIGHT - self.image.get_height()))

    #     # Update amplitudes based on new position
    #     position_ratio = self.rect.y / (HEIGHT - self.image.get_height())
    #     angle = position_ratio * (FLEX_SENSOR_MAX - FLEX_SENSOR_MIN) + FLEX_SENSOR_MIN
    #     self.amplitudes.append((angle, angle))


    def handle_collision(self):
        """Make the bird temporarily invincible and reduce lives."""
        self.is_invincible = True
        self.invincible_start_time = pygame.time.get_ticks()
        self.lives -= 1
        print(f"Collision detected! Lives remaining: {self.lives}")


    def check_invincibility(self):
        """Disable invincibility after the set duration."""
        if self.is_invincible:
            current_time = pygame.time.get_ticks()
            if current_time - self.invincible_start_time > INVINCIBLE_DURATION:
                self.is_invincible = False

    def draw(self, screen):
        """Draw the sprite, blinking when invincible."""
        if self.is_invincible:
            current_time = pygame.time.get_ticks()
            if (current_time // BLINK_INTERVAL) % 2 == 0:
                screen.blit(self.image, self.rect.topleft)
        else:
            screen.blit(self.image, self.rect.topleft)

    def pass_obstacle(self):
        """Increment the obstacle counter."""
        self.obstacles_passed += 1
        print(f"Obstacle passed! Total obstacles passed: {self.obstacles_passed}")

# class Wood(pygame.sprite.Sprite):
#     def __init__(self, image, x, y, bottom):
#         super().__init__()
#         self.image = image
#         self.rect = self.image.get_rect()
#         self.rect.topleft = (x, y)
#         self.initial_x = x  # Store initial x position
#         self.bottom = bottom
#         self.passed = False

#     def update(self):
#         self.rect.x -= 3  # Fixed speed
#         if self.rect.right < 0:
#             self.rect.x = self.initial_x  # Reset to initial position
#             self.passed = False
class Wood(pygame.sprite.Sprite):
    """Obstacle sprite representing a wood trunk."""

    def __init__(self, image, x, y, bottom):
        """Create a wood obstacle at ``x, y``."""
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)  # Posição diretamente do CSV
        self.initial_x = x  # Armazena a posição inicial para referência
        self.passed = False  # Para saber se o jogador já passou pelo tronco

    def update(self):
        """Move the wood to the left and remove when off screen."""
        self.rect.x -= 3  # Velocidade fixa para mover à esquerda
        if self.rect.right < 0:  # Saiu da tela
            self.kill()  # Remove o sprite da lista de ativos (não reseta mais)

    def draw(self, screen):
        """Blit the sprite image at its position."""
        screen.blit(self.image, self.rect.topleft)


class Cloud(pygame.sprite.Sprite):
    """Background cloud sprite."""

    def __init__(self, image, x, y, speed):
        """Create a cloud image at ``x, y`` moving with ``speed``."""
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.speed = speed

    def update(self):
        """Move the cloud across the screen."""
        self.rect.x -= self.speed
        if self.rect.right < 0:
            self.rect.left = WIDTH

    def draw(self, screen):
        """Draw the cloud on ``screen``."""
        screen.blit(self.image, self.rect.topleft)
