"""Convenience imports for the :mod:`Modules` package."""

from .ble_manager import *  # noqa: F401,F403
from .calibration_manager import *  # noqa: F401,F403
from .goniometer_manager import *  # noqa: F401,F403
from .sensor_data import *  # noqa: F401,F403
from .tests import *  # noqa: F401,F403
# Legacy Tk GUI desativada: comentar import para evitar dependência de plot_manager Tk
# from .gui_manager import *  # noqa: F401,F403
from .fsr_calibrador import FSRCalibrador  # noqa: F401

# Removido: from .plot_manager import *
# O antigo PlotManager (Tk) e versões intermediárias foram movidos para pasta legacy.
# A versão atualmente usada na UI PyQt6 é importada diretamente onde necessária:
# from Modules.plot_manager_qt_old import PlotManagerQtOld

# Opcional: expor subpacote legacy se existir
try:  # pragma: no cover - apenas conveniência
	from .legacy import *  # noqa: F401,F403
except Exception:
	pass
