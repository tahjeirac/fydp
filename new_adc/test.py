import pigpio
import numpy as np
import matplotlib.pyplot as plt
import time

SPI_BUS = 0  # SPI bus (0 or 1)
CHANNEL = 1  # ADC channel to read from

# Initialize pigpio and connect
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

# Open SPI connection (1 MHz SPI clock)
spi_handle = pi.spi_open(SPI_BUS, 1000000, 0)

SAMPLE_FREQ = 20000  # Target sample rate in Hz
VREF = 3.3  # Reference voltage
BIT_DEPTH = 12  # MCP3208 is 12-bit
DURATION = 1  # 1 ms of data collection
SAMPLES = int(SAMPLE_FREQ * DURATION)  # Number of samples

# Function to read ADC value
def read_adc(channel):
    """Reads a value from the ADC using SPI"""
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    result = pi.spi_xfer(spi_handle, command)
    adc_value = ((result[1][1] & 0x0F) << 8) | result[1][2]
    return adc_value

def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2**BIT_DEPTH - 1))

# **Waveform-Based Sampling using pigpio.wave_add_generic()**
pi.wave_clear()  # Clear any existing waveforms

# Generate SPI read waveforms at precise intervals
wave = []

for i in range(SAMPLES):
    wave.append(pigpio.pulse(1 << 4, 0, int(5e6 / SAMPLE_FREQ)))  # GPIO 4 as a dummy trigger

pi.wave_add_generic(wave)  # Add waveform
wave_id = pi.wave_create()  # Create wave from pulses

# **Trigger the waveform sampling**
if wave_id >= 0:
    pi.wave_send_once(wave_id)  # Send waveform one time

# **Read SPI Data after Waveform Execution**
voltages = np.zeros(SAMPLES)
times = np.linspace(0, DURATION, SAMPLES) * 1000  # Time array in ms

for i in range(SAMPLES):
    voltages[i] = convert_to_voltage(read_adc(CHANNEL))

# **Cleanup**
pi.wave_delete(wave_id)  # Remove waveform
pi.spi_close(spi_handle)
pi.stop()

# **Remove DC Offset**
voltages -= np.mean(voltages)

# **Plot the results**
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
fft_result /= np.max(fft_result)  # Normalize
frequencies = np.fft.fftfreq(SAMPLES, 1 / SAMPLE_FREQ)

# **Keep only positive frequencies**
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
# frequencies = np.fft.fftshift(np.fft.fftfreq(SAMPLES, 1 / SAMPLE_FREQ))

plt.subplot(3, 1, 3)
plt.plot(frequencies, magnitude, 'b-')
plt.title("Frequency Domain: Magnitude Spectrum")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.grid(True)
plt.xlim(0, SAMPLE_FREQ / 2)  # Limit to Nyquist frequency
plt.tight_layout()
plt.show()
