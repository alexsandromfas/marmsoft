"""Graphical interface manager for sensor visualization and calibration.

This module defines :class:`GUIManager`, responsible for orchestrating the
CustomTkinter based interface used in the application.  It handles BLE
connections, goniometer data acquisition and provides access to calibration
and test tools.
"""

import customtkinter as ctk
import threading
import time
import asyncio
from .plot_manager import PlotManager
from .legacy.calibration_manager import CalibrationManager
from .goniometer_manager import GoniometerManager
from .tests import Tests
from .ble_manager import BLEManager
from .fsr_calibrador import FSRCalibrador
from bleak import BleakScanner
import tkinter as tk

CHARACTERISTIC_UUID = "abcdef01-1234-5678-1234-56789abcdef0"

class GUIManager:
    """Manage the graphical user interface and sensor interactions.

    Parameters
    ----------
    root : tkinter.Tk
        Root window for all widgets.
    sensors : dict
        Mapping of sensor identifiers to :class:`SensorData` instances.
    latest_readings : dict
        Dictionary where the latest processed sensor values are stored.
    """

    def __init__(self, root, sensors, latest_readings):
        """Initialize the GUI manager with sensor mappings.

        Parameters
        ----------
        root : tkinter.Tk
            Main application window.
        sensors : dict
            Dictionary of sensors keyed by identifier.
        latest_readings : dict
            Shared dictionary storing the latest sensor values.
        """

        self.root = root
        self.sensors = sensors
        self.latest_readings = latest_readings
        self.is_paused = False
        self.ble_manager = None
        self.ble_device_address = None
        self.plot_mode = tk.StringVar(value="flex")  # "flex" ou "fsr"
        self.displayed_sensors = set(sensors.keys()) 

        self.goniometer = GoniometerManager(
            dll_path=r"C:\Program Files (x86)\Biometrics Ltd\DataLITE\OnLineInterface64.dll",
            channel=0
        )

        if self.goniometer.dll:
            self.goniometer.start_reading()

        self.sensor_vars = {}
        for sensor_id in self.sensors.keys():
            self.sensor_vars[sensor_id] = tk.BooleanVar(value=True)

        self.goniometer_var = tk.BooleanVar(value=True)
        self.visualizacao_frame_open = False

        self.setup_ui()
        self.update_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Create menu bar, plotting widgets and calibration options."""
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)

        self.bluetooth_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Bluetooth", menu=self.bluetooth_menu)
        self.bluetooth_menu.add_command(label="Conectar...", command=self.open_bluetooth_window)

        self.appearance_mode = tk.StringVar(value="Dark")
        self.appearance_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Aparência", menu=self.appearance_menu)
        self.appearance_menu.add_radiobutton(label="Dark", variable=self.appearance_mode, command=self.change_appearance_mode, value="Dark")
        self.appearance_menu.add_radiobutton(label="Light", variable=self.appearance_mode, command=self.change_appearance_mode, value="Light")

        self.jogos_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Jogos", menu=self.jogos_menu)
        self.jogos_menu.add_radiobutton(label="FlyBird", command=self.open_game)

        self.calibracoes_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Calibrações", menu=self.calibracoes_menu)
        flex_sensors_menu = tk.Menu(self.calibracoes_menu, tearoff=0)
        self.calibracoes_menu.add_cascade(label="Flex Sensors", menu=flex_sensors_menu)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True)

        self.plot_manager = PlotManager(self.main_frame, time_window=10, sensors=self.sensors, displayed_sensors=self.displayed_sensors)
        self.calibration_manager = CalibrationManager(self.root, self.sensors, self.latest_readings)

        for sensor_id in self.sensors.keys():
            flex_sensors_menu.add_command(
                label=f"{sensor_id.upper()}",
                command=lambda s=sensor_id: self.calibration_manager.open_calibration_window(s)
            )

        self.setup_controls()

    def setup_controls(self):
        """Add buttons and sensor selection check boxes to the GUI."""
        self.frame_controls = ctk.CTkFrame(self.main_frame, width=300)
        self.frame_controls.pack(side="right", fill="y")

        self.visualizacao_frame = ctk.CTkFrame(self.main_frame)

        self.visualizacao_button = ctk.CTkButton(
            self.frame_controls,
            text="Visualização",
            command=self.toggle_visualizacao_frame
        )
        self.visualizacao_button.pack(pady=10)

        ctk.CTkLabel(self.frame_controls, text="Modo de Plotagem").pack(pady=5)
        flex_plot_rb = ctk.CTkRadioButton(
            self.frame_controls,
            text="FlexPlot",
            variable=self.plot_mode,
            value="flex",
            command=self.update_displayed_sensors
        )
        flex_plot_rb.pack(pady=5)

        fsr_plot_rb = ctk.CTkRadioButton(
            self.frame_controls,
            text="FSRPlot",
            variable=self.plot_mode,
            value="fsr",
            command=self.update_displayed_sensors
        )
        fsr_plot_rb.pack(pady=5)

        ctk.CTkCheckBox(
            self.visualizacao_frame,
            text="GONIÔMETRO",
            variable=self.goniometer_var,
            command=self.update_displayed_sensors
        ).pack(anchor='w', padx=10, pady=5)

        for sensor_id in self.sensors.keys():
            ctk.CTkCheckBox(
                self.visualizacao_frame,
                text=sensor_id.upper(),
                variable=self.sensor_vars[sensor_id],
                command=self.update_displayed_sensors
            ).pack(anchor='w', padx=10, pady=5)

        clear_button = ctk.CTkButton(self.frame_controls, text="Limpar Dados", command=self.clear_data)
        clear_button.pack(pady=10)

        test_button = ctk.CTkButton(self.frame_controls, text="Testes", command=self.open_tests)
        test_button.pack(pady=10)

        ctk.CTkLabel(self.frame_controls, text="Suavização").pack(pady=10)
        smoothing_slider = ctk.CTkSlider(
            self.frame_controls, from_=0.01, to=1, number_of_steps=100,
            command=self.adjust_smoothing
        )
        if 'flex1' in self.sensors:
            smoothing_slider.set(self.sensors['flex1'].alpha)
        smoothing_slider.pack(pady=10)

    def toggle_visualizacao_frame(self):
        """Show or hide the sensor selection frame."""
        if self.visualizacao_frame_open:
            self.visualizacao_frame.pack_forget()
            self.visualizacao_frame_open = False
            self.visualizacao_button.configure(fg_color=None)
        else:
            self.visualizacao_frame.pack(side='right', fill='y')
            self.visualizacao_frame_open = True
            self.visualizacao_button.configure(fg_color="gray30")

    def change_appearance_mode(self, *args):
        """Switch between dark and light UI themes."""
        mode = self.appearance_mode.get()
        ctk.set_appearance_mode(mode)

    def open_bluetooth_window(self):
        """Display a window listing available Bluetooth devices."""
        self.bluetooth_window = ctk.CTkToplevel(self.root)
        self.bluetooth_window.title("Dispositivos Bluetooth")
        self.bluetooth_window.geometry("400x300")

        self.bluetooth_window.lift()
        self.bluetooth_window.attributes('-topmost', True)
        self.bluetooth_window.after(10, lambda: self.bluetooth_window.attributes('-topmost', False))

        ctk.CTkLabel(self.bluetooth_window, text="Dispositivos Disponíveis:").pack(pady=10)
        self.devices_listbox = tk.Listbox(self.bluetooth_window)
        self.devices_listbox.pack(fill="both", expand=True, padx=10, pady=5)

        refresh_button = ctk.CTkButton(self.bluetooth_window, text="Atualizar Lista", command=self.scan_devices)
        refresh_button.pack(pady=5)

        connect_button = ctk.CTkButton(self.bluetooth_window, text="Conectar", command=self.connect_device)
        connect_button.pack(pady=5)

        self.scan_devices()

    def scan_devices(self):
        """Populate the Bluetooth window with discovered devices."""
        async def discover():
            from bleak import BleakScanner
            devices = await BleakScanner.discover()
            self.devices_list = devices
            self.devices_listbox.delete(0, 'end')
            for idx, device in enumerate(devices):
                display_name = device.name or "Desconhecido"
                self.devices_listbox.insert('end', f"{display_name} ({device.address})")

        def run_discover():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(discover())
            loop.close()

        threading.Thread(target=run_discover).start()

    def connect_device(self):
        """Connect to the Bluetooth device selected in the list box."""
        selection = self.devices_listbox.curselection()
        if selection:
            idx = selection[0]
            device_address = self.devices_list[idx].address
            self.ble_device_address = device_address
            self.start_ble(self.ble_device_address)
            self.bluetooth_window.destroy()

    def start_ble(self, device_address):
        """Start the BLE manager thread for the given device."""
        if self.ble_manager is not None:
            self.ble_manager.stop_loop()
        self.ble_manager = BLEManager(device_address, CHARACTERISTIC_UUID, self.notification_handler)
        threading.Thread(target=self.ble_manager.start_loop, daemon=True).start()

    # def notification_handler(self, sender, data):
    #     decoded_data = data.decode("utf-8")
    #     try:
    #         values = decoded_data.split(", ")
    #         for value in values:
    #             sensor_name, voltage_str = value.split("=")
    #             voltage = float(voltage_str[:-1])  
    #             sensor_id = sensor_name.lower()

    #             if sensor_id in self.sensors:
    #                 filtered_voltage = self.sensors[sensor_id].apply_filter(voltage)
    #                 self.latest_readings[f'{sensor_id}_voltage'] = filtered_voltage

    #                 if sensor_id.startswith('flex'):
    #                     angle = self.sensors[sensor_id].get_angle(filtered_voltage)
    #                     self.latest_readings[f'{sensor_id}_angle'] = angle
    #                 elif sensor_id.startswith('fsr'):
    #                     force = filtered_voltage * 1000.0
    #                     self.latest_readings[f'{sensor_id}_force'] = force
    #     except Exception as e:
    #         print(f"Erro ao processar dados: {e}")


    def notification_handler(self, sender, data):
        """Process BLE notifications and update sensor readings."""
        decoded_data = data.decode("utf-8")
        try:
            values = decoded_data.split(", ")
            for value in values:
                sensor_name, voltage_str = value.split("=")
                voltage = float(voltage_str[:-1])  
                sensor_id = sensor_name.lower()

                if sensor_id in self.sensors:
                    filtered_voltage = self.sensors[sensor_id].apply_filter(voltage)
                    self.latest_readings[f'{sensor_id}_voltage'] = filtered_voltage

                    if sensor_id.startswith('flex'):
                        angle = self.sensors[sensor_id].get_angle(filtered_voltage)
                        self.latest_readings[f'{sensor_id}_angle'] = angle
                    elif sensor_id.startswith('fsr'):
                        # Agora usamos get_force para aplicar a calibração polinomial se existir
                        force = self.sensors[sensor_id].get_force(filtered_voltage)
                        self.latest_readings[f'{sensor_id}_force'] = force
        except Exception as e:
            print(f"Erro ao processar dados: {e}")



    def clear_data(self):
        """Clear all data from the plots."""
        self.plot_manager.clear()

    def adjust_smoothing(self, value):
        """Change the low pass filter constant for all sensors."""
        for sensor in self.sensors.values():
            sensor.alpha = float(value)
        print(f"Nível de suavização ajustado para: {value}")

    def open_game(self):
        """Launch the FlyBird mini-game in a separate thread."""
        import threading
        from FlyBird.main_fb import main_fb
        def run_game():
            main_fb(sensor_data_provider=lambda: self.get_flex_angle('flex6'))
        threading.Thread(target=run_game, daemon=True).start()

    def get_flex_angle(self, sensor_id):
        """Return the latest angle for a flex sensor."""
        return self.latest_readings.get(f'{sensor_id}_angle', 0.0)

    def open_tests(self):
        """Open the testing window for the flex sensors."""
        tests = Tests(self.root, sensors=self.sensors, latest_readings=self.latest_readings, goniometer=self.goniometer)
        tests.open_tests_window()

    def update_gui(self):
        """Refresh plots and schedule the next GUI update."""
        if not self.is_paused:
            current_time = time.time()
            if self.goniometer.dll:
                self.latest_readings['goniometer_angle'] = self.goniometer.get_angle()
            else:
                self.latest_readings['goniometer_angle'] = 0

            self.plot_manager.set_mode(self.plot_mode.get())
            self.plot_manager.update(current_time, self.latest_readings)

        self.root.after(10, self.update_gui)

    def on_closing(self):
        """Handle application shutdown and resource cleanup."""
        if self.goniometer.dll:
            self.goniometer.stop_reading()
        if self.ble_manager is not None:
            self.ble_manager.stop_loop()
        self.root.destroy()

    def update_displayed_sensors(self):
        """Update which sensors are visible on the plots."""
        chosen_sensors = set()
        for sensor_id, var in self.sensor_vars.items():
            if var.get():
                chosen_sensors.add(sensor_id)

        if self.plot_mode.get() == "flex":
            # modo flex: flex + goniometro se marcado
            if self.goniometer_var.get():
                chosen_sensors.add('goniometer')
            else:
                if 'goniometer' in chosen_sensors:
                    chosen_sensors.remove('goniometer')
            final_sensors = {s for s in chosen_sensors if s.startswith('flex') or s == 'goniometer'}
        else:
            # modo fsr: apenas fsr
            if 'goniometer' in chosen_sensors:
                chosen_sensors.remove('goniometer')
            final_sensors = {s for s in chosen_sensors if s.startswith('fsr')}

        self.displayed_sensors = final_sensors
        self.plot_manager.update_displayed_sensors(self.displayed_sensors)
