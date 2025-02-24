import time
import numpy as np
import pigpio
import matplotlib.pyplot as plt

# Set up pigpio and configure SPI settings
pi = pigpio.pi()  # Create an instance of pigpio
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI bus (0 or 1)
SAMPLE_FREQ = 500000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window

pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution

SAMPLE_RATE = 1000  # Samples per second (Adjust for smooth plotting)
SINE_WAVE_FREQ = 250  # Frequency of sine wave (250 Hz)
DURATION = 1 / SINE_WAVE_FREQ  # Plot duration to cover one sine wave period (in seconds)
SAMPLES = int(SAMPLE_RATE * DURATION)  # Number of samples to collect (based on duration)

# Function to read data from MCP3208 using pigpio SPI
def read_adc(channel):
    """Reads a value from the ADC using SPI with DMA"""
    # ADC command for MCP3208 (12-bit ADC)
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    
    # Send the command to the ADC
    result = pi.spi_xfer(SPI_BUS, command)
    
    # Convert the result to 12-bit value
    value = (result[1][1] & 0x0F) << 8 | result[1][2]
    
    return value

def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2 ** BIT_DEPTH - 1))

# Data storage
times = np.linspace(0, DURATION, SAMPLES)  # Time array for one period
voltages = np.zeros(SAMPLES)  # Placeholder for voltage values

# Collect all data before plotting
for i in range(SAMPLES):
    adc_value = read_adc(0)  # Read ADC value from channel 0
    voltage = convert_to_voltage(adc_value)
    voltages[i] = voltage
    time.sleep(1 / SAMPLE_RATE)  # Ensure proper sample rate

# Plot the data after collection
plt.figure(figsize=(10, 6))
plt.plot(times, voltages, 'r-')
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title("Captured ADC Data (Sine Wave)")
plt.grid(True)
plt.show()

# Clean up
pi.stop()  # Stop pigpio connection
print("Cleaned up resources.")
