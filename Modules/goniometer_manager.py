# Modules/goniometer_manager.py

import ctypes
from ctypes import POINTER, byref, c_int
import threading
import time

class GoniometerManager:
    def __init__(self, dll_path, channel=0):
        self.dll_path = dll_path
        self.channel = channel
        self.angle = 0
        self.running = False
        self.dll = None

        # Tentar carregar a DLL
        try:
            self.dll = ctypes.WinDLL(self.dll_path)
            # Configurações das funções da DLL
            self.OnLineStatus = self.dll.OnLineStatus
            self.OnLineStatus.argtypes = [c_int, c_int, POINTER(c_int)]
            self.OnLineStatus.restype = c_int

            # Constantes da DLL
            self.OLI_ONLINE_GETVALUE = 4
            self.OLI_ONLINE_OK = 0
            self.OLI_ONLINE_START = 5
            self.OLI_ONLINE_STOP = 6
        except OSError as e:
            print(f"Erro ao carregar a DLL do goniômetro: {e}")
            self.dll = None  # Continua a execução mesmo se não conseguir carregar a DLL

    def start_reading(self):
        """Inicia a leitura do goniômetro em uma thread separada."""
        if self.running or not self.dll:
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_data)
        self.thread.daemon = True
        self.thread.start()

    def stop_reading(self):
        """Para a leitura do goniômetro."""
        if not self.dll:
            return
        self.running = False
        self.OnLineStatus(self.channel, self.OLI_ONLINE_STOP, None)

    def _read_data(self):
        """Função que lê dados do goniômetro continuamente."""
        if not self.dll:
            return
        # Inicia a transferência
        result = self.OnLineStatus(self.channel, self.OLI_ONLINE_START, None)
        if result != self.OLI_ONLINE_OK:
            print(f"Erro ao iniciar transferência no canal {self.channel}: {result}")
            return

        try:
            while self.running:
                valor_atual = c_int()
                result = self.OnLineStatus(self.channel, self.OLI_ONLINE_GETVALUE, byref(valor_atual))
                if result == self.OLI_ONLINE_OK:
                    self.angle = self._converter_para_graus(valor_atual.value)
                else:
                    print(f"Erro ao obter valor no canal {self.channel}: {result}")
                time.sleep(0.05)  # Leitura a cada 50 ms
        except Exception as e:
            print(f"Erro na leitura do goniômetro: {e}")
        finally:
            self.stop_reading()

    def _converter_para_graus(self, valor_bruto):
        """Converte o valor bruto do goniômetro para graus."""
        valor_convertido = int((valor_bruto / 4000) * 180)
        return valor_convertido

    def get_angle(self):
        """Retorna o último ângulo lido."""
        return self.angle
