# modules/utils.py

import pygame
import os
import random
from FlyBird.modules.settings import *
import csv

def extract_number(filename):
    try:
        return int("".join(filter(str.isdigit, filename)))
    except ValueError:
        return 0
    
def load_obstacles_from_csv():
    obstacles = []
    csv_file = os.path.join(DATA_DIR, 'obstacles.csv')
    if not os.path.exists(csv_file):
        print(f"Obstacle CSV file not found: {csv_file}")
        return obstacles

    with open(csv_file, 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            obstacle_type = row['type']
            filename = row['filename']
            x = int(row['x'])
            y = int(row['y'])
            bottom = row['bottom'].lower() == 'true'
            if obstacle_type == 'wood':
                img = pygame.image.load(os.path.join(WOOD_DIR, filename)).convert_alpha()
                scale_factor = 0.4
                img = pygame.transform.scale(
                    img,
                    (int(img.get_width() * scale_factor), int(img.get_height() * scale_factor))
                )
                obstacles.append({'image': img, 'x': x, 'y': y, 'bottom': bottom})

            # if obstacle_type == 'wood':
            #     img = pygame.image.load(os.path.join(WOOD_DIR, filename)).convert_alpha()
            #     scale_factor = 0.4
            #     img = pygame.transform.scale(
            #         img,
            #         (int(img.get_width() * scale_factor),
            #          int(img.get_height() * scale_factor))
            #     )
            #     if not bottom:
            #         img = pygame.transform.flip(img, False, True)
            #     obstacles.append({'image': img, 'x': x, 'y': y, 'bottom': bottom})
            # Handle other obstacle types if needed
    return obstacles


def remove_background_with_tolerance(surface, base_color, tolerance):
    surface = surface.copy()
    surface.lock()
    width, height = surface.get_size()
    for x in range(width):
        for y in range(height):
            color = surface.get_at((x, y))
            if all(abs(color[i] - base_color[i]) <= tolerance for i in range(3)):
                surface.set_at((x, y), (0, 0, 0, 0))
    surface.unlock()
    return surface

def load_images_from_folder(folder, scale_factor=1.0, remove_bg=False, base_color=(0, 255, 0)):
    images = []
    for file in sorted(os.listdir(folder), key=extract_number):
        if file.endswith(".png"):
            path = os.path.join(folder, file)
            image = pygame.image.load(path).convert_alpha()
            if scale_factor != 1.0:
                image = pygame.transform.scale(
                    image,
                    (int(image.get_width() * scale_factor),
                     int(image.get_height() * scale_factor))
                )
            if remove_bg:
                image = remove_background_with_tolerance(image, base_color, TOLERANCE)
            images.append(image)
    return images

def generate_clouds(cloud_images):
    clouds = []
    for _ in range(10):
        img = random.choice(cloud_images)
        scale_factor = random.uniform(0.5, 1.5)
        img = pygame.transform.scale(
            img,
            (int(img.get_width() * scale_factor),
             int(img.get_height() * scale_factor))
        )
        layer = random.choice(["front", "middle", "back"])
        speed = {"front": 2, "middle": 1.5, "back": 1}[layer]
        y_pos = random.randint(50, HEIGHT - 200)
        clouds.append({"image": img, "x": random.randint(0, WIDTH), "y": y_pos, "speed": speed})
    return clouds



# def generate_woods(wood_images):
#     woods = []
#     x_position = WIDTH  # Start off-screen
#     scale_factor = 0.4
#     while len(woods) < 5:
#         img = random.choice(wood_images)
#         img = pygame.transform.scale(
#             img,
#             (int(img.get_width() * scale_factor),
#              int(img.get_height() * scale_factor))
#         )
#         bottom_trunk = random.choice([True, False])
#         if bottom_trunk:
#             y_position = HEIGHT - img.get_height()
#         else:
#             y_position = -10
#             img = pygame.transform.flip(img, False, True)
#         woods.append({"image": img, "x": x_position, "y": y_position, "bottom": bottom_trunk})
#         x_position += random.randint(200, 400)
#     return woods

def generate_woods():
    woods = []
    obstacles = load_obstacles_from_csv()
    for obstacle_data in obstacles:
        if obstacle_data['bottom']:
            wood = {
                "image": obstacle_data['image'],
                "x": obstacle_data['x'],
                "y": obstacle_data['y'],
                "bottom": obstacle_data['bottom']
            }
            print(f"Wood generated at x={wood['x']}, y={wood['y']}")
            woods.append(wood)
    return woods
