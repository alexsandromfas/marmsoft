"""Global constants used throughout the FlyBird game."""

import os
import sys

# Screen settings
WIDTH, HEIGHT = 960, 640
FPS = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Paths
def _get_base_dir():
    """Retorna diretório base do FlyBird, compatível com PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Executável congelado pelo PyInstaller
        # PyInstaller coloca os dados em _MEIPASS (pasta _internal)
        meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        return os.path.join(meipass, 'FlyBird')
    else:
        # Modo de desenvolvimento
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = _get_base_dir()
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
NUVENS_DIR = os.path.join(ASSETS_DIR, "Nuvens")
BIRD_DIR = os.path.join(ASSETS_DIR, "Bird")
WOOD_DIR = os.path.join(ASSETS_DIR, "Woods")
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_FILE = os.path.join(DATA_DIR, "results.csv")
RESULTS_JSON = os.path.join(DATA_DIR, "results.json")

# Bird settings
BIRD_SCALE = 0.15  # Scale to reduce bird size
BIRD_FRAME_RATE = 50
BIRD_ACCELERATION = 0.3
BIRD_MAX_SPEED = 5
BIRD_FRICTION = 0.1

# Invincibility settings
INVINCIBLE_DURATION = 3000  # milliseconds
BLINK_INTERVAL = 300  # milliseconds

# Lives
INITIAL_LIVES = 2

# Flex Sensor settings
FLEX_SENSOR_MIN = 0     # Minimum angle (degrees)
FLEX_SENSOR_MAX = 90    # Maximum angle (degrees)
FLEX_SENSOR_CENTER = 45 # Center position
# modules/settings.py

# Sensor angle ranges for bird movement
SENSOR_ANGLE_MIN = 280  # Minimum angle from sensor to start moving the bird
SENSOR_ANGLE_MAX = 170  # Maximum angle from sensor

# Other settings
TOLERANCE = 20  # Tolerance for background removal
