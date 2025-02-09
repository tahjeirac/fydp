import time
import numpy as np
import matplotlib.pyplot as plt
import pigpio

# Initialize pigpio and SPI
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI Bus
SPI_CS = 8   # Chip Select pin
VREF = 3.3  # ADC reference voltage
BIT_DEPTH = 12  # MCP3208 has 12-bit resolution
SAMPLE_COUNT = 1000  # Number of samples to collect
SAMPLE_FREQ = 44100  # Sample frequency in Hz

# Open SPI connection
pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, Mode 0

# Function to read ADC value
def read_adc(channel):
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    result = pi.spi_xfer(SPI_BUS, command)
    value = (result[1][1] & 0x0F) << 8 | result[1][2]
    return value

# Collect ADC samples
adc_values = []
timestamps = []
start_time = time.time()

for _ in range(SAMPLE_COUNT):
    adc_value = read_adc(channel=0)  # Read from channel 0
    adc_values.append(adc_value)
    print (adc_value)
    timestamps.append(time.time() - start_time)
    time.sleep(1 / SAMPLE_FREQ)  # Maintain correct sampling rate

# Convert ADC values to voltage
adc_voltages = [VREF * (val / (2**BIT_DEPTH - 1)) for val in adc_values]

# Plot the ADC waveform
plt.figure(figsize=(10, 6))
plt.plot(timestamps, adc_value, label="Microphone Signal")
plt.xlabel("Time (seconds)")
plt.ylabel("Voltage (V)")
plt.title("ADC Output Over Time")
plt.legend()
plt.grid()
plt.show()

# Cleanup
pi.stop()
