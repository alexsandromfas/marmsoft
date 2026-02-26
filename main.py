"""Entry point atualizado para UI PyQt6.

Esta versão desativa a antiga interface CustomTkinter (gui_manager.py) e inicializa
a interface PyQt6 consolidada. Mantém criação e calibração dos sensores para uso
nas funcionalidades migradas (BLE, plots, calibração, testes) que serão
acopladas progressivamente dentro de `ui_manager.MainWindow`.
"""

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMessageBox
from PyQt6.QtGui import QPalette, QColor, QPixmap
from PyQt6.QtCore import Qt, QTimer
import os
import sys
import traceback
import logging
from datetime import datetime
from Modules.sensor_data import SensorData
from Modules.goniometer_manager import GoniometerManager
from Modules import ui_manager  # módulo renomeado (antes ui_prototipo)

# -------- Função para obter diretório base correto --------
def get_base_dir():
    """Retorna o diretório base correto tanto em desenvolvimento quanto no executável PyInstaller."""
    if getattr(sys, 'frozen', False):
        # Executável PyInstaller - usa o diretório do executável
        return os.path.dirname(sys.executable)
    else:
        # Desenvolvimento - usa o diretório do script
        return os.path.dirname(os.path.abspath(__file__))

# -------- Configuração de logging --------
def setup_logging(base_dir):
    """Configura logging para arquivo, útil para debug do executável."""
    try:
        log_dir = os.path.join(base_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'marmsoft_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logging.info(f"Logging iniciado: {log_file}")
        return log_file
    except Exception as e:
        print(f"Erro ao configurar logging: {e}")
        traceback.print_exc()
        return None

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
    BASE_DIR = get_base_dir()
    log_file = setup_logging(BASE_DIR)
    
    try:
        logging.info("=" * 60)
        logging.info("INICIANDO MARMSOFT")
        logging.info(f"Python: {sys.version}")
        logging.info(f"Sistema: {sys.platform}")
        logging.info(f"Frozen: {getattr(sys, 'frozen', False)}")
        logging.info(f"Base Dir: {BASE_DIR}")
        logging.info("=" * 60)
        
        # -------- Criação e calibração de sensores --------
        logging.info("Criando sensores...")
        sensors = {f"flex{i}": SensorData() for i in range(1,9)}
        sensors.update({f"fsr{i}": SensorData() for i in range(1,5)})
        sensors['load_cell'] = SensorData()
        logging.info(f"Sensores criados: {len(sensors)} sensores")

        # Carrega calibrações
        logging.info("Carregando calibrações dos sensores...")
        calib_loaded = 0
        for i in range(1,9):
            calib_path = os.path.join(BASE_DIR, "calibrations", "flex", f"calibration_flex{i}.csv")
            if os.path.isfile(calib_path):
                try:
                    sensors[f"flex{i}"].load_calibration_from_file(calib_path)
                    calib_loaded += 1
                except Exception as e:
                    logging.warning(f"Erro ao carregar calibração flex{i}: {e}")
            else:
                logging.warning(f"Calibração não encontrada: {calib_path}")

        for i in range(1,5):
            calib_path = os.path.join(BASE_DIR, "calibrations", "fsr", f"calibration_fsr{i}.csv")
            if os.path.isfile(calib_path):
                try:
                    sensors[f"fsr{i}"].load_calibration_from_file(calib_path)
                    calib_loaded += 1
                except Exception as e:
                    logging.warning(f"Erro ao carregar calibração fsr{i}: {e}")
            else:
                logging.warning(f"Calibração não encontrada: {calib_path}")

        logging.info(f"Calibrações carregadas: {calib_loaded} de 12")

        latest_readings = {"goniometer_angle":0.0}
        for i in range(1,9):
            latest_readings[f"flex{i}_voltage"] = 0.0
            latest_readings[f"flex{i}_angle"] = 0.0
        for i in range(1,5):
            latest_readings[f"fsr{i}_voltage"] = 0.0
            latest_readings[f"fsr{i}_force"] = 0.0
        latest_readings['load_cell_force'] = 0.0
        logging.info("Latest readings inicializadas")
        
        app = QApplication(sys.argv)
        logging.info("QApplication criada")
        
        # Tema dark básico compatível com interface
        pal = app.palette()
        pal.setColor(QPalette.ColorRole.Window, QColor('#121212'))
        pal.setColor(QPalette.ColorRole.WindowText, QColor('#eeeeee'))
        pal.setColor(QPalette.ColorRole.Base, QColor('#1e1e1e'))
        pal.setColor(QPalette.ColorRole.Text, QColor('#dddddd'))
        app.setPalette(pal)
        logging.info("Tema aplicado")

        # Tenta carregar ícone para splash
        icon_path = os.path.join(BASE_DIR, 'assets', 'icon.png')
        splash = None
        if os.path.isfile(icon_path):
            logging.info(f"Ícone encontrado: {icon_path}")
            pm = QPixmap(icon_path)
            if not pm.isNull():
                # Reduz altura pela metade mantendo proporção
                target_height = pm.height() // 2
                if target_height > 0:
                    pm = pm.scaledToHeight(target_height, Qt.TransformationMode.SmoothTransformation)
                splash = _ImageSplash(pm)
                splash.show()
                logging.info("Splash screen exibida")
        else:
            logging.warning(f"Ícone não encontrado: {icon_path}")

        # Inicia goniômetro (opcional) durante splash
        logging.info("Inicializando goniômetro...")
        goniometer = GoniometerManager(
            dll_path=r"C:\Program Files (x86)\Biometrics Ltd\DataLITE\OnLineInterface64.dll",
            channel=0
        )
        if goniometer.dll:
            goniometer.start_reading()
            logging.info("Goniômetro iniciado")
        else:
            logging.warning("Goniômetro não disponível")

        def _show_main():
            try:
                logging.info("Criando janela principal...")
                win = ui_manager.MainWindow(sensors=sensors, latest_readings=latest_readings, goniometer=goniometer)
                if splash:
                    splash.close()
                    logging.info("Splash fechada")
                win.show()
                logging.info("Janela principal exibida")
                # Mantém referência para evitar garbage collection
                app.win = win  # type: ignore
            except Exception as e:
                logging.error(f"ERRO ao criar janela principal: {e}")
                logging.error(traceback.format_exc())
                if splash:
                    splash.close()
                QMessageBox.critical(
                    None, 
                    "Erro Fatal", 
                    f"Erro ao iniciar aplicação:\n\n{str(e)}\n\nVerifique o log em:\n{log_file}"
                )
                sys.exit(1)

        # Agenda abertura da janela principal em 3 segundos (3000 ms) ou imediata se sem splash
        delay_ms = 3000 if splash else 0
        logging.info(f"Agendando abertura da janela principal em {delay_ms}ms")
        QTimer.singleShot(delay_ms, _show_main)

        logging.info("Entrando no event loop...")
        sys.exit(app.exec())
        
    except Exception as e:
        logging.critical(f"ERRO FATAL no main(): {e}")
        logging.critical(traceback.format_exc())
        try:
            QMessageBox.critical(
                None,
                "Erro Fatal",
                f"Erro crítico ao iniciar MarmSoft:\n\n{str(e)}\n\n"
                f"Verifique o log em:\n{log_file if log_file else 'logs/'}\n\n"
                f"Traceback completo no log."
            )
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()

