import time
import pigpio
import numpy as np
import matplotlib.pyplot as plt

# Initialize pigpio
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

# SPI Configuration
SPI_BUS = 0  
SPI_SPEED = 1000000  # 1 MHz
VREF = 3.3  # ADC Reference Voltage
BIT_DEPTH = 12  # 12-bit ADC
SAMPLE_RATE = 100  # How many samples per second
DURATION = 5  # Plot duration in seconds
SAMPLES = SAMPLE_RATE * DURATION  # Total samples to collect

# Open SPI connection
# adc_handle = pi.spi_open(SPI_BUS, SPI_SPEED, 0)
pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)

def read_adc(channel=0):
    """Reads a 12-bit ADC value from MCP3208 via SPI"""
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    # (count, data) = pi.spi_xfer(SPI_BUS, command)
    
    result = pi.spi_xfer(SPI_BUS, command)

    # Convert the result to 12-bit value
    value = (result[1][1] & 0x0F) << 8 | result[1][2]
    
    return value

def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2 ** BIT_DEPTH - 1))

# Data storage
times = []
voltages = []

# Matplotlib Setup
plt.ion()  # Enable interactive mode
fig, ax = plt.subplots()
ax.set_xlim(0, DURATION)
ax.set_ylim(0, VREF)
ax.set_xlabel("Time (s)")
ax.set_ylabel("Voltage (V)")
ax.set_title("Constant Voltage Test")

line, = ax.plot([], [], 'r-')

start_time = time.time()

try:
    print("Reading ADC... Apply a constant voltage and observe the plot.")
    while time.time() - start_time < DURATION:
        elapsed_time = time.time() - start_time
        adc_value = read_adc()
        voltage = convert_to_voltage(adc_value)
        print (voltage)
        times.append(elapsed_time)
        voltages.append(voltage)

        # Update plot
        line.set_data(times, voltages)
        ax.set_xlim(0, elapsed_time + 0.5)  # Adjust x-axis dynamically
        plt.draw()
        plt.pause(0.01)

    plt.ioff()  # Disable interactive mode
    plt.show()

except KeyboardInterrupt:
    print("\nInterrupted by user.")
finally:
    pi.stop()
    print("Cleaned up resources.")
