"""Entry point atualizado para UI PyQt6.

Esta versão desativa a antiga interface CustomTkinter (gui_manager.py) e inicializa
a interface PyQt6 consolidada. Mantém criação e calibração dos sensores para uso
nas funcionalidades migradas (BLE, plots, calibração, testes) que serão
acopladas progressivamente dentro de `ui_manager.MainWindow`.
"""

from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import Qt, QTimer
import os
import sys
from Modules.sensor_data import SensorData
from Modules.goniometer_manager import GoniometerManager
from Modules import ui_manager  # módulo renomeado (antes ui_prototipo)

# -------- Criação e calibração de sensores (reutilizado) --------
sensors = {f"flex{i}": SensorData() for i in range(1,9)}
sensors.update({f"fsr{i}": SensorData() for i in range(1,5)})
# Adiciona sensor lógico da célula de carga (sem calibração inicial)
sensors['load_cell'] = SensorData()

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
# Load cell (inicializa força em N)
latest_readings['load_cell_force'] = 0.0

class _ImageSplash(QWidget):
    """Splash simples que mostra apenas uma imagem PNG com transparência.

    A janela é sem bordas e transparente fora da área da imagem.
    """
    def __init__(self, pixmap: QPixmap):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.label = QLabel(self)
        self.label.setPixmap(pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.resize(pixmap.size())
        # Centraliza na tela principal
        screen_geo = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen_geo.x() + (screen_geo.width() - self.width()) // 2,
            screen_geo.y() + (screen_geo.height() - self.height()) // 2
        )

def main():
    app = QApplication(sys.argv)
    # Tema dark básico compatível com interface
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window, QColor('#121212'))
    pal.setColor(QPalette.ColorRole.WindowText, QColor('#eeeeee'))
    pal.setColor(QPalette.ColorRole.Base, QColor('#1e1e1e'))
    pal.setColor(QPalette.ColorRole.Text, QColor('#dddddd'))
    app.setPalette(pal)

    # Tenta carregar ícone para splash
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'icon.png')
    splash = None
    if os.path.isfile(icon_path):
        pm = QPixmap(icon_path)
        if not pm.isNull():
            # Reduz altura pela metade mantendo proporção
            target_height = pm.height() // 2
            if target_height > 0:
                pm = pm.scaledToHeight(target_height, Qt.TransformationMode.SmoothTransformation)
            splash = _ImageSplash(pm)
            splash.show()

    # Inicia goniômetro (opcional) durante splash
    goniometer = GoniometerManager(
        dll_path=r"C:\Program Files (x86)\Biometrics Ltd\DataLITE\OnLineInterface64.dll",
        channel=0
    )
    if goniometer.dll:
        goniometer.start_reading()

    def _show_main():
        win = ui_manager.MainWindow(sensors=sensors, latest_readings=latest_readings, goniometer=goniometer)
        if splash:
            splash.close()
        win.show()
        # Mantém referência para evitar garbage collection
        app.win = win  # type: ignore

    # Agenda abertura da janela principal em 2 segundos (2000 ms) ou imediata se sem splash
    delay_ms = 5000 if splash else 0
    QTimer.singleShot(delay_ms, _show_main)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

