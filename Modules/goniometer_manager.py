"""Interface with the Biometrics Ltd goniometer device."""

import ctypes
from ctypes import POINTER, byref, c_int
import threading
import time

class GoniometerManager:
    """Handle asynchronous reading of a hardware goniometer."""

    def __init__(self, dll_path, channel=0):
        """Create a new manager.

        Parameters
        ----------
        dll_path : str
            Path to the vendor DLL that provides the API.
        channel : int, optional
            Channel index used to read the goniometer.
        """
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
        """Start reading the goniometer values in a background thread."""
        if self.running or not self.dll:
            return
        self.running = True
        self.thread = threading.Thread(target=self._read_data)
        self.thread.daemon = True
        self.thread.start()

    def stop_reading(self):
        """Stop the reading thread and close the device connection."""
        if not self.dll:
            return
        self.running = False
        self.OnLineStatus(self.channel, self.OLI_ONLINE_STOP, None)

    def _read_data(self):
        """Continuously poll the device for angle data."""
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
        """Convert a raw goniometer value to degrees."""
        valor_convertido = int((valor_bruto / 4000) * 180)
        return valor_convertido

    def get_angle(self):
        """Return the most recently read angle."""
        return self.angle
