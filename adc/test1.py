import time
import numpy as np
import pigpio
import matplotlib.pyplot as plt

SPI_BUS = 0  # SPI bus (0 or 1)
CHANNEL = 0  # ADC channel to read from

# Set up pigpio and configure SPI settings
pi = pigpio.pi()  
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

# Open SPI connection (1 MHz SPI clock)
spi_handle = pi.spi_open(SPI_BUS, 1000000, 0)

SAMPLE_FREQ = 20000  # Sampling rate in Hz
VREF = 3.3  # Reference voltage
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
DURATION = 1 / 1000  # 1 ms of data collection
SAMPLES = int(SAMPLE_FREQ * DURATION)  # Number of samples

# Function to read ADC data
def read_adc(channel):
    """Reads a value from the ADC using SPI"""
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    result = pi.spi_xfer(spi_handle, command)
    adc_value = ((result[1][1] & 0x0F) << 8) | result[1][2]
    return adc_value

def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2**BIT_DEPTH - 1))

# Data storage
times = np.linspace(0, DURATION, SAMPLES) * 1000  # Time array in ms
voltages = np.zeros(SAMPLES)  # Placeholder for voltage values

# **High-Precision Sampling Loop**
start_time = time.perf_counter()
for i in range(SAMPLES):
    voltages[i] = convert_to_voltage(read_adc(CHANNEL))  # Read and store voltage
    
    # High-precision timing
    while (time.perf_counter() - start_time) < ((i + 1) / SAMPLE_FREQ):
        pass  # Busy-wait to maintain exact sampling rate

# Stop SPI communication
pi.spi_close(spi_handle)
pi.stop()

# Remove DC offset (center the signal around 0)
voltages -= np.mean(voltages)

# Plot the data after collection
plt.figure(figsize=(10, 6))

# **Time-Domain Plot**
plt.subplot(3, 1, 1)
plt.plot(times, voltages, 'r-')
plt.xlabel("Time (ms)")
plt.ylabel("Voltage (V)")
plt.title("Captured ADC Data (Sine Wave)")
plt.grid(True)

# **FFT Calculation**
fft_result = np.abs(np.fft.fft(voltages))
fft_result = fft_result / np.max(fft_result)  # Normalize
frequencies = np.fft.fftfreq(SAMPLES, 1 / SAMPLE_FREQ)

# Keep only positive frequencies
positive_freqs = frequencies[:SAMPLES // 2]
positive_fft = fft_result[:SAMPLES // 2]

# **Frequency Spectrum Plot**
plt.subplot(3, 1, 2)
plt.plot(positive_freqs, positive_fft, 'b-')
plt.xlabel("Frequency (Hz)")
plt.ylabel("Amplitude")
plt.title("Frequency Spectrum of ADC Input")
plt.grid(True)

# **Magnitude Spectrum Plot**
fft_values = np.fft.fftshift(np.fft.fft(voltages))
magnitude = np.fft.fftshift(np.abs(fft_values))
frequencies = np.fft.fftshift(np.fft.fftfreq(SAMPLES, 1 / SAMPLE_FREQ))

plt.subplot(3, 1, 3)
plt.plot(frequencies, magnitude, 'b-')
plt.title("Frequency Domain: Magnitude Spectrum")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.grid(True)
plt.xlim(0, SAMPLE_FREQ / 2)  # Limit to Nyquist frequency
plt.tight_layout()
plt.show()
