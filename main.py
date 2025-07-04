# main.py

import customtkinter as ctk
import threading
import time
from Modules.sensor_data import SensorData
from Modules.gui_manager import GUIManager

# Configurações BLE
CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

sensors = {}

# Criar 8 Flex Sensors
for i in range(1, 9):
    sensors[f'flex{i}'] = SensorData()

# Criar 4 FSR Sensors
for i in range(1, 5):
    sensors[f'fsr{i}'] = SensorData()

# Carregar calibrações flex
for i in range(1, 9):
    sensors[f'flex{i}'].load_calibration_from_file(f'calibration_flex{i}.csv')

# Carregar calibrações fsr (se existir)
for i in range(1, 5):
    sensors[f'fsr{i}'].load_calibration_from_file(f'calibration_fsr{i}.csv')

latest_readings = {'goniometer_angle': 0.0}

# Flex readings
for i in range(1, 9):
    latest_readings[f'flex{i}_voltage'] = 0.0
    latest_readings[f'flex{i}_angle'] = 0.0

# FSR readings
for i in range(1, 5):
    latest_readings[f'fsr{i}_voltage'] = 0.0
    latest_readings[f'fsr{i}_force'] = 0.0  # novo campo para força

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
root.title("MarmSoft")
root.state("zoomed")

gui_manager = GUIManager(
    root=root,
    sensors=sensors,
    latest_readings=latest_readings
)

root.mainloop()
