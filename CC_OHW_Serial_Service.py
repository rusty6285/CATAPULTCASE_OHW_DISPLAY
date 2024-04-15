import time
import serial
import wmi
import win32com.client

# Function to get current temperature in Celsius for a specific sensor type and label
def get_temperature(sensor_type, label):
    # Get the OpenHardwareMonitor WMI object
    wmi_obj = win32com.client.GetObject("winmgmts://./root/OpenHardwareMonitor")

    # Get the temperature sensors
    sensors = wmi_obj.InstancesOf("Sensor")

    for sensor in sensors:
        if sensor.SensorType == sensor_type and label in sensor.Name:
            return sensor.Value

    return None

# Function to get fan speed in RPM for a specific sensor type and label
def get_fan_speed(sensor_type, label):
    w = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
    sensors = w.Sensor()

    for sensor in sensors:
        if sensor.SensorType == sensor_type and label in sensor.Name:
            return sensor.Value

    return None

# Function to send data to Arduino
def send_to_arduino(ser, data):
    ser.write(data)

# Main function
def main():
    # Initialize serial connection to Arduino
    try:
        ser = serial.Serial('COM5', 9600, timeout=1)
    except serial.SerialException as e:
        print("Failed to connect to Arduino:", e)
        return

    print("Connected to Arduino on COM5")

    while True:
        # Get CPU temperature
        cpu_temp = get_temperature('Temperature', 'CPU')
        if cpu_temp is not None:
            cpu_temp_str = "{:.1f}".format(cpu_temp).encode()  # Format to one decimal place
            # Send CPU temperature to Arduino
            send_to_arduino(ser, cpu_temp_str)
            print("Sent CPU temperature:", cpu_temp_str.decode())
        else:
            print("Failed to get CPU temperature.")

        # Get GPU temperature
        gpu_temp = get_temperature('Temperature', 'GPU')
        if gpu_temp is not None:
            gpu_temp_str = "{:.1f}".format(gpu_temp).encode()  # Format to one decimal place
            # Send GPU temperature to Arduino
            send_to_arduino(ser, gpu_temp_str)
            print("Sent GPU temperature:", gpu_temp_str.decode())
        else:
            print("Failed to get GPU temperature.")

        # Get GPU fan speed
        gpu_fan_speed = get_fan_speed('Fan', 'GPU')
        if gpu_fan_speed is not None:
            gpu_fan_speed_str = str(gpu_fan_speed).encode()
            # Send GPU fan speed to Arduino
            send_to_arduino(ser, gpu_fan_speed_str)
            print("Sent GPU fan speed:", gpu_fan_speed_str.decode())
        else:
            print("Failed to get GPU fan speed.")

        time.sleep(1)  # Adjust interval as needed

if __name__ == "__main__":
    main()
