import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import QTimer
import serial.tools.list_ports
import psutil
import wmi
import win32com.client


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CATAPULTCASE OHW MONITOR")
        self.setGeometry(100, 100, 400, 400)

        # Hide the console window
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

        # Create labels
        self.openhardware_label = QLabel("OpenHardwareMonitor Detected: No", self)
        self.openhardware_label.setGeometry(20, 20, 250, 30)

        # Create COM Port selection dropdown
        self.com_label = QLabel("Select Display COM Port:", self)
        self.com_label.setGeometry(20, 60, 150, 30)

        self.com_port_combo = QComboBox(self)
        self.com_port_combo.setGeometry(150, 60, 200, 30)
        self.com_port_combo.setMinimumWidth(200)

        # Create GPU selection dropdown
        self.gpu_label = QLabel("Select GPU:", self)
        self.gpu_label.setGeometry(20, 100, 150, 30)

        self.gpu_combo = QComboBox(self)
        self.gpu_combo.setGeometry(150, 100, 200, 30)
        self.gpu_combo.setMinimumWidth(200)
        self.gpu_combo.setEnabled(False)  # Initially disabled

        # Create status label
        self.status_label = QLabel("Status: Thinking...", self)
        self.status_label.setGeometry(20, 140, 300, 30)

        # Create Start/Stop button
        self.start_stop_button = QPushButton("Start", self)
        self.start_stop_button.setGeometry(20, 180, 100, 30)
        self.start_stop_button.setEnabled(False)  # Initially disabled
        self.start_stop_button.clicked.connect(self.toggle_monitoring)

        # Create Log table
        self.log_table = QTableWidget(self)
        self.log_table.setGeometry(20, 220, 350, 150)
        self.log_table.setColumnCount(2)
        self.log_table.setHorizontalHeaderLabels(["Parameter", "Value"])

        # Initialize serial connection
        self.ser = None

        # Initialize QTimer for periodic updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.timer.start(1000)

        # Initialize QTimer for checking OpenHardwareMonitor availability
        self.timer_check_openhardwaremonitor = QTimer(self)
        self.timer_check_openhardwaremonitor.timeout.connect(self.detect_openhardwaremonitor)
        self.timer_check_openhardwaremonitor.start(5000)  # Check every 5 seconds

        # Update COM port dropdown with available ports
        self.update_com_ports()

        # Flag to track monitoring state
        self.monitoring = False

    def detect_openhardwaremonitor(self):
        openhardwaremonitor_running = any(
            process.info['name'] == 'OpenHardwareMonitor.exe' for process in psutil.process_iter(['pid', 'name']))

        if openhardwaremonitor_running:
            self.openhardware_label.setText("OpenHardwareMonitor Detected: Yes")
            self.start_stop_button.setEnabled(True)  # Enable Start button
            if not self.monitoring:
                self.gpu_combo.setEnabled(True)  # Enable GPU picklist only if not monitoring
            self.update_gpu_list()
            if not self.monitoring:
                self.status_label.setText("Status: Idle - Ready to Start")
        else:
            self.openhardware_label.setText("OpenHardwareMonitor Detected: No")
            self.start_stop_button.setEnabled(False)  # Disable Start button
            self.gpu_combo.clear()
            self.gpu_combo.addItem("Not detected")
            self.gpu_combo.setEnabled(False)  # Disable GPU picklist
            if not self.monitoring:
                self.status_label.setText("Error: Is OpenHardwareMonitor Running?")

        if not openhardwaremonitor_running and self.monitoring:
            self.stop_monitoring()
            self.com_port_combo.setEnabled(True)  # Enable COM port picklist if not monitoring

    def update_com_ports(self):
        self.com_port_combo.clear()
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.com_port_combo.addItems(ports)

    def update_gpu_list(self):
        self.gpu_combo.clear()
        wmi_obj = win32com.client.GetObject("winmgmts://./root/OpenHardwareMonitor")
        sensors = wmi_obj.InstancesOf("Hardware")
        detected_gpus = []
        for sensor in sensors:
            if sensor.Identifier.startswith("/nvidiagpu/") or sensor.Identifier.startswith("/amdgpu/"):
                detected_gpus.append(sensor.Name)
        self.gpu_combo.addItems(detected_gpus)
        if not detected_gpus:
            self.gpu_combo.addItem("None")

    def toggle_monitoring(self):
        if not self.monitoring:
            self.start_monitoring()
            self.com_port_combo.setEnabled(False)
            self.gpu_combo.setEnabled(False)
        else:
            self.stop_monitoring()
            self.com_port_combo.setEnabled(True)
            if not self.openhardware_label.text() == "OpenHardwareMonitor Detected: No":
                self.gpu_combo.setEnabled(True)  # Enable GPU picklist if OpenHardwareMonitor detected

    def start_monitoring(self):
        com_port = self.com_port_combo.currentText()
        try:
            self.ser = serial.Serial(com_port, 9600, timeout=1)
            self.status_label.setText("Status: Connected via Serial")
            self.monitoring = True
            self.start_stop_button.setText("Stop")
        except serial.SerialException as e:
            self.status_label.setText(f"Status: Failed to connect to Arduino: {e}")

    def stop_monitoring(self):
        if self.ser:
            self.ser.close()
        self.status_label.setText("Status: Thinking...")
        self.monitoring = False
        self.start_stop_button.setText("Start")

    def update_values(self):
        cpu_temp = self.get_temperature('Temperature', 'CPU')
        gpu_temp = self.get_temperature('Temperature', 'GPU')
        gpu_fan_speed = self.get_fan_speed('Fan', 'GPU')

        self.log_table.setRowCount(0)

        if cpu_temp is not None:
            cpu_temp_str = "{:.1f}".format(cpu_temp)
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem("CPU Temperature"))
            self.log_table.setItem(row, 1, QTableWidgetItem(cpu_temp_str))
            self.send_to_arduino(cpu_temp_str)

        if gpu_temp is not None:
            gpu_temp_str = "{:.1f}".format(gpu_temp)
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem("GPU Temperature"))
            self.log_table.setItem(row, 1, QTableWidgetItem(gpu_temp_str))
            self.send_to_arduino(gpu_temp_str)

        if gpu_fan_speed is not None:
            gpu_fan_speed_str = str(gpu_fan_speed)
            row = self.log_table.rowCount()
            self.log_table.insertRow(row)
            self.log_table.setItem(row, 0, QTableWidgetItem("GPU Fan Speed"))
            self.log_table.setItem(row, 1, QTableWidgetItem(gpu_fan_speed_str))
            self.send_to_arduino(gpu_fan_speed_str)

    def get_temperature(self, sensor_type, label):
        wmi_obj = win32com.client.GetObject("winmgmts://./root/OpenHardwareMonitor")
        sensors = wmi_obj.InstancesOf("Sensor")
        for sensor in sensors:
            if sensor.SensorType == sensor_type and label in sensor.Name:
                return sensor.Value
        return None

    def get_fan_speed(self, sensor_type, label):
        w = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
        sensors = w.Sensor()
        for sensor in sensors:
            if sensor.SensorType == sensor_type and label in sensor.Name:
                return sensor.Value
        return None

    def send_to_arduino(self, data):
        if self.monitoring and self.ser:
            self.ser.write(data.encode())
            print(f"Sent data to Arduino: {data}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
