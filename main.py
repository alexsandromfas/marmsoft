"""Entry point atualizado para UI PyQt6.

Esta versão desativa a antiga interface CustomTkinter (gui_manager.py) e inicializa
a interface PyQt6 consolidada. Mantém criação e calibração dos sensores para uso
nas funcionalidades migradas (BLE, plots, calibração, testes) que serão
acopladas progressivamente dentro de `ui_manager.MainWindow`.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
import sys
from Modules.sensor_data import SensorData
from Modules.goniometer_manager import GoniometerManager
from Modules import ui_manager  # módulo renomeado (antes ui_prototipo)

# -------- Criação e calibração de sensores (reutilizado) --------
sensors = {f"flex{i}": SensorData() for i in range(1,9)}
sensors.update({f"fsr{i}": SensorData() for i in range(1,5)})

for i in range(1,9):
    sensors[f"flex{i}"].load_calibration_from_file(f"calibration_flex{i}.csv")
for i in range(1,5):
    sensors[f"fsr{i}"].load_calibration_from_file(f"calibration_fsr{i}.csv")

latest_readings = {"goniometer_angle":0.0}
for i in range(1,9):
    latest_readings[f"flex{i}_voltage"] = 0.0
    latest_readings[f"flex{i}_angle"] = 0.0
for i in range(1,5):
    latest_readings[f"fsr{i}_voltage"] = 0.0
    latest_readings[f"fsr{i}_force"] = 0.0

def main():
    app = QApplication(sys.argv)
    # Tema dark básico compatível com protótipo
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor('#121212'))
    pal.setColor(QPalette.ColorRole.WindowText, QColor('#eeeeee'))
    pal.setColor(QPalette.ColorRole.Base, QColor('#1e1e1e'))
    pal.setColor(QPalette.ColorRole.Text, QColor('#dddddd'))
    app.setPalette(pal)

    # Inicia goniômetro (opcional)
    goniometer = GoniometerManager(
        dll_path=r"C:\Program Files (x86)\Biometrics Ltd\DataLITE\OnLineInterface64.dll",
        channel=0
    )
    if goniometer.dll:
        goniometer.start_reading()

    win = ui_manager.MainWindow(sensors=sensors, latest_readings=latest_readings, goniometer=goniometer)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
