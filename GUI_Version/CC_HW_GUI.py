import sys
import json
import os
import serial.tools.list_ports
import psutil
import win32com.client
import pythoncom
import serial
import winreg
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QAction, QMenu, QSystemTrayIcon
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon

class SerialThread(QThread):
    error_signal = pyqtSignal(str)  # Signal to emit error messages

    def __init__(self, com_port):
        super().__init__()
        self.com_port = com_port
        self.ser = None

    def run(self):
        try:
            self.ser = serial.Serial(self.com_port, 9600, timeout=1)
        except serial.SerialException as e:
            self.error_signal.emit(f"Serial connection error: {e}")

    def send_values(self, values):
        if self.ser and self.ser.is_open:
            try:
                serialized_values = json.dumps(values)
                self.ser.write(serialized_values.encode())
            except Exception as e:
                self.error_signal.emit(f"Error sending values over serial connection: {e}")

    def close_serial(self):
        if self.ser:
            self.ser.close()

class ValueUpdateThread(QThread):
    update_values_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()

    def run(self):
        while True:
            cpu_temp = self.get_temperature('Temperature', 'CPU')
            gpu_temp = self.get_temperature('Temperature', 'GPU')
            gpu_fan_speed = self.get_fan_speed('Fan', 'GPU')

            values = {}
            if cpu_temp is not None:
                values["cpu_temp"] = "{:.1f}".format(cpu_temp)

            if gpu_temp is not None:
                values["gpu_temp"] = "{:.1f}".format(gpu_temp)

            if gpu_fan_speed is not None:
                values["gpu_fan_rpm"] = str(gpu_fan_speed)

            self.update_values_signal.emit(values)

            self.sleep(10)

    def get_temperature(self, sensor_type, label):
        try:
            pythoncom.CoInitialize()
            wmi_obj = win32com.client.GetObject("winmgmts:\\\\.\\root\\OpenHardwareMonitor")
            sensors = wmi_obj.InstancesOf("Sensor")
            for sensor in sensors:
                if sensor.SensorType == sensor_type and label in sensor.Name:
                    return sensor.Value
        except Exception as e:
            print(f"Error accessing OpenHardwareMonitor WMI namespace: {e}")
        return None

    def get_fan_speed(self, sensor_type, label):
        try:
            pythoncom.CoInitialize()
            wmi_obj = win32com.client.GetObject("winmgmts:\\\\.\\root\\OpenHardwareMonitor")
            sensors = wmi_obj.InstancesOf("Sensor")
            for sensor in sensors:
                if sensor.SensorType == sensor_type and label in sensor.Name:
                    return sensor.Value
        except Exception as e:
            print(f"Error accessing OpenHardwareMonitor WMI namespace: {e}")
        return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CATAPULTCASE OHW MONITOR")
        self.setFixedSize(400, 550)

        print("Loading preferences...")
        self.preferences = load_preferences()
        print("Preferences loaded:", self.preferences)

        self.openhardware_label = QLabel("OpenHardwareMonitor Detected: No", self)
        self.openhardware_label.setGeometry(20, 20, 250, 30)

        self.com_label = QLabel("Select Display COM Port:", self)
        self.com_label.setGeometry(20, 60, 150, 30)

        self.com_port_combo = QComboBox(self)
        self.com_port_combo.setGeometry(150, 60, 200, 30)
        self.com_port_combo.setMinimumWidth(200)

        self.gpu_label = QLabel("Select GPU:", self)
        self.gpu_label.setGeometry(20, 100, 150, 30)

        self.gpu_combo = QComboBox(self)
        self.gpu_combo.setGeometry(150, 100, 200, 30)
        self.gpu_combo.setMinimumWidth(200)
        self.gpu_combo.setEnabled(False)

        self.status_label = QLabel("Status: Thinking...", self)
        self.status_label.setGeometry(20, 140, 300, 30)

        self.start_stop_button = QPushButton("Start", self)
        self.start_stop_button.setGeometry(20, 180, 100, 30)
        self.start_stop_button.setEnabled(False)
        self.start_stop_button.clicked.connect(self.toggle_monitoring)

        self.run_on_startup_checkbox = QCheckBox("Run when Windows starts", self)
        self.run_on_startup_checkbox.setGeometry(20, 220, 250, 30)
        self.run_on_startup_checkbox.setChecked(self.preferences.get("run_on_startup", False))
        self.run_on_startup_checkbox.stateChanged.connect(self.toggle_startup_registry)

        self.auto_start_serial_checkbox = QCheckBox("Attempt to Auto-Start Serial Connection", self)
        self.auto_start_serial_checkbox.setGeometry(20, 260, 250, 30)
        self.auto_start_serial_checkbox.setChecked(self.preferences.get("auto_start_serial", False))
        self.auto_start_serial_checkbox.stateChanged.connect(self.toggle_auto_start_serial)

        self.auto_start_countdown_label = QLabel("", self)
        self.auto_start_countdown_label.setGeometry(280, 260, 100, 30)
        self.auto_start_countdown_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.auto_start_countdown_label.hide()

        self.start_minimized_checkbox = QCheckBox("Start Minimized", self)
        self.start_minimized_checkbox.setGeometry(20, 300, 150, 30)
        self.start_minimized_checkbox.setChecked(self.preferences.get("start_minimized", False))
        self.start_minimized_checkbox.stateChanged.connect(self.save_start_minimized_preference)

        self.log_table = QTableWidget(self)
        self.log_table.setGeometry(20, 340, 350, 150)
        self.log_table.setColumnCount(2)
        self.log_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setColumnWidth(0, 200)

        self.serial_thread = SerialThread("")
        self.serial_thread.error_signal.connect(self.handle_serial_error)

        self.value_update_thread = ValueUpdateThread()
        self.value_update_thread.update_values_signal.connect(self.update_values)

        self.value_update_thread.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.timer.start(10000)

        self.timer_check_openhardwaremonitor = QTimer(self)
        self.timer_check_openhardwaremonitor.timeout.connect(self.detect_openhardwaremonitor)
        self.timer_check_openhardwaremonitor.start(5000)

        self.initialize_com_ports()

        self.monitoring = False

        self.auto_start_countdown = 10
        self.auto_start_timer = QTimer(self)
        self.auto_start_timer.timeout.connect(self.update_auto_start_countdown)

        self.auto_start_countdown_active = False

        if self.preferences.get("auto_start_serial", False):
            self.toggle_auto_start_serial(Qt.Checked)

        self.com_port_combo.currentIndexChanged.connect(self.update_com_port_selection)

        print("Initialization complete.")

        self._init_completed = True

    def initialize_com_ports(self):
        print("[Initialization] Method 'initialize_com_ports' - Initializing COM ports...")
        current_selection = self.preferences.get("com_port", "")
        print("[Initialization] Method 'initialize_com_ports' - Current selection from preferences:", current_selection)
        self.com_port_combo.clear()
        retrieved_ports = [port.device for port in serial.tools.list_ports.comports()]
        print("[Initialization] Method 'initialize_com_ports' - Retrieved COM ports:", retrieved_ports)
        ports_with_descriptions = [f"{port.device} - {port.description}" for port in serial.tools.list_ports.comports()]
        self.com_port_combo.addItems(ports_with_descriptions)
        if current_selection:
            print(f"[Initialization] Method 'initialize_com_ports' - Stored current selection: {current_selection}")
            com_ports = [port.split(" - ")[0] for port in ports_with_descriptions]
            if current_selection in com_ports:
                index = com_ports.index(current_selection)
                print(f"[Initialization] Method 'initialize_com_ports' - Found a match for the stored selection: {current_selection}")
                self.com_port_combo.setCurrentIndex(index)
                print(f"[Initialization] Method 'initialize_com_ports' - Updated current selection: {current_selection}")
            else:
                print(f"[Initialization] Method 'initialize_com_ports' - Failed to find a match for the stored selection: {current_selection}")

        print("[Initialization] Method 'initialize_com_ports' - COM port updated:", self.com_port_combo.currentText())

    def update_com_port_selection(self, index):
        if index != -1:
            com_port = self.com_port_combo.currentText().split(" ")[0]
            self.preferences["com_port"] = com_port
            self.save_preferences()
            print(f"[{'Initialization' if self._init_completed else 'Runtime'}] Method 'update_com_port_selection' - COM port selection changed:", com_port)

    def detect_openhardwaremonitor(self):
        openhardwaremonitor_running = any(
            process.info['name'] == 'OpenHardwareMonitor.exe' for process in psutil.process_iter(['pid', 'name']))

        if openhardwaremonitor_running:
            self.openhardware_label.setText("OpenHardwareMonitor Detected: Yes")
            self.start_stop_button.setEnabled(True)
            if not self.monitoring:
                self.gpu_combo.setEnabled(True)
                self.com_port_combo.setEnabled(True)
            self.update_gpu_list()
            if not self.monitoring:
                self.status_label.setText("Status: Idle - Ready to Start")
        else:
            self.openhardware_label.setText("OpenHardwareMonitor Detected: No")
            self.start_stop_button.setEnabled(False)
            self.gpu_combo.clear()
            self.gpu_combo.addItem("Not detected")
            self.gpu_combo.setEnabled(False)
            if not self.monitoring:
                self.status_label.setText("Error: Is OpenHardwareMonitor Running?")

        if not openhardwaremonitor_running and self.monitoring:
            self.stop_monitoring()
            self.com_port_combo.setEnabled(True)

    def update_gpu_list(self):
        self.gpu_combo.clear()
        try:
            pythoncom.CoInitialize()
            wmi_obj = win32com.client.GetObject("winmgmts:\\\\.\\root\\OpenHardwareMonitor")
            sensors = wmi_obj.InstancesOf("Hardware")
            detected_gpus = []
            for sensor in sensors:
                if sensor.Identifier.startswith("/nvidiagpu/") or sensor.Identifier.startswith("/amdgpu/"):
                    detected_gpus.append(sensor.Name)
            self.gpu_combo.addItems(detected_gpus)
            if not detected_gpus:
                self.gpu_combo.addItem("None")
        except Exception as e:
            print(f"Error accessing OpenHardwareMonitor WMI namespace: {e}")

    def toggle_monitoring(self):
        if not self.monitoring:
            self.start_monitoring()
            self.com_port_combo.setEnabled(False)
            self.gpu_combo.setEnabled(False)
            self.auto_start_countdown_label.hide()
            self.stop_auto_start_timer()
            if self.auto_start_countdown_active:
                self.stop_auto_start_countdown()
        else:
            self.stop_monitoring()
            self.com_port_combo.setEnabled(True)
            if not self.openhardware_label.text() == "OpenHardwareMonitor Detected: No":
                self.gpu_combo.setEnabled(True)

    def start_monitoring(self):
        com_port = self.com_port_combo.currentText().split(" ")[0]
        self.serial_thread.com_port = com_port
        self.serial_thread.start()

        self.status_label.setText("Status: Connected via Serial (Updates every 10 seconds)")
        self.monitoring = True
        self.start_stop_button.setText("Stop")

    def stop_monitoring(self):
        self.serial_thread.close_serial()

        self.status_label.setText("Status: Thinking...")
        self.monitoring = False
        self.start_stop_button.setText("Start")

    def update_values(self, values=None):
        if values is None:
            return
        self.log_table.setRowCount(0)
        for parameter, value in values.items():
            self.add_log_row(parameter, value)
        if self.monitoring:
            self.serial_thread.send_values(values)

    def add_log_row(self, parameter, value):
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)
        self.log_table.setItem(row, 0, QTableWidgetItem(parameter))
        self.log_table.setItem(row, 1, QTableWidgetItem(value))

    def toggle_startup_registry(self, state):
        self.preferences["run_on_startup"] = state == Qt.Checked
        self.save_preferences()

        key = winreg.HKEY_CURRENT_USER
        key_value = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "OHWMonitor"

        if state == Qt.Checked:
            try:
                key_obj = winreg.OpenKey(key, key_value, 0, winreg.KEY_WRITE)
                winreg.SetValueEx(key_obj, app_name, 0, winreg.REG_SZ, sys.executable)
                key_obj.Close()
            except Exception as e:
                print(f"Error toggling startup registry: {e}")
        else:
            try:
                key_obj = winreg.OpenKey(key, key_value, 0, winreg.KEY_WRITE)
                winreg.DeleteValue(key_obj, app_name)
                key_obj.Close()
            except Exception as e:
                print(f"Error toggling startup registry: {e}")

    def toggle_auto_start_serial(self, state):
        self.preferences["auto_start_serial"] = state == Qt.Checked
        self.save_preferences()

        if state == Qt.Checked and not self.monitoring:
            self.auto_start_countdown_label.show()
            self.auto_start_timer.start(1000)
            self.auto_start_countdown_active = True
        else:
            self.auto_start_countdown_label.hide()
            self.auto_start_timer.stop()
            self.auto_start_countdown_active = False

    def update_auto_start_countdown(self):
        self.auto_start_countdown -= 1
        self.auto_start_countdown_label.setText(f"Trying in {self.auto_start_countdown} seconds")
        if self.auto_start_countdown <= 0:
            self.auto_start_timer.stop()
            self.toggle_monitoring()
            self.auto_start_countdown_label.hide()
            self.auto_start_countdown = 10
            self.auto_start_countdown_active = False

    def stop_auto_start_timer(self):
        self.auto_start_timer.stop()
        self.auto_start_countdown_label.hide()
        self.auto_start_countdown = 10
        self.auto_start_countdown_active = False

    def save_start_minimized_preference(self, state):
        self.preferences["start_minimized"] = state == Qt.Checked
        self.save_preferences()

    def save_preferences(self):
        preferences_path = os.path.join(os.getenv("APPDATA"), "CATAPULTCASE", "preferences.json")
        os.makedirs(os.path.dirname(preferences_path), exist_ok=True)
        with open(preferences_path, "w") as file:
            json.dump(self.preferences, file, indent=4)
        print("Preferences saved:", self.preferences)

    def handle_serial_error(self, error_message):
        self.status_label.setText(error_message)
        self.stop_monitoring()
        QMessageBox.critical(self, "Serial Connection Error", error_message)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

def load_preferences():
    preferences_path = os.path.join(os.getenv("APPDATA"), "CATAPULTCASE", "preferences.json")
    try:
        with open(preferences_path, "r") as file:
            preferences = json.load(file)
    except FileNotFoundError:
        preferences = {
            "com_port": "",
            "run_on_startup": False,
            "auto_start_serial": False,
            "start_minimized": False
        }
        with open(preferences_path, "w") as file:
            json.dump(preferences, file, indent=4)
    return preferences

def run():
    app = QApplication(sys.argv)
    main_window = MainWindow()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, 'CC_Logo.png')
    tray_icon = QSystemTrayIcon(QIcon(icon_path), parent=app)
    tray_icon.setToolTip("CATAPULTCASE OHW MONITOR")
    # print("Icon Path has been saved as", icon_path)
    # print("Script Path has been saved as", script_dir)
    
    menu = QMenu()
    show_action = QAction("Show", parent=app)
    exit_action = QAction("Exit", parent=app)
    
    show_action.triggered.connect(main_window.show)
    exit_action.triggered.connect(app.quit)
    
    menu.addAction(show_action)
    menu.addAction(exit_action)
    
    tray_icon.setContextMenu(menu)
    tray_icon.show()
    
    # Check if the preference for starting minimized is set
    if main_window.preferences.get("start_minimized", False):
        main_window.hide()  # Start minimized
    else:
        main_window.show()  # Start unminimized
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    run()
