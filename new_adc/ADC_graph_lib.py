import pigpio
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft

from adc import MCP3208Gpiozero, MCP3208Spidev


# Record data for 2 seconds
duration = 0.01  # Record for 2 seconds
sample_rate = 48000  # Number of samples per second (adjust this depending on your ADC)
num_samples = int(duration * sample_rate)

# Store the readings
time_data = np.linspace(0, duration, num_samples)
amplitude_data = []
volts = []
adc_gzero = MCP3208Gpiozero()


def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return 3.3 * (adc_value / (2**12 - 1))
# Read ADC data and store amplitude values
start_time = time.time()
while len(amplitude_data) < num_samples:
    adc_value = adc_gzero.read(1)  # Read from channel 0 (you can change the channel)
    # Normalize the ADC value to a range (e.g., 0-3.3V for a 3.3V reference voltage)
    amplitude = (adc_value / 4095.0) * 3.3  # Assuming 12-bit ADC and 3.3V reference
    volts.append(convert_to_voltage(adc_value))
    amplitude_data.append(amplitude)
    time.sleep(1/sample_rate)


# Save amplitude data to a file
with open("amplitude_data.txt", "w") as f:
    for value in amplitude_data:
        f.write(f"{value}\n")

print("Amplitude data saved to amplitude_data.txt")


plt.figure(figsize=(10, 6))
plt.subplot(3, 1, 1)
plt.plot(time_data, amplitude_data)
plt.title('Amplitude vs Time')
plt.xlabel('Time [s]')
plt.ylabel('Amplitude [V]')
plt.grid(True)

# Perform FFT (Discrete Fourier Transform)
fft_data = np.fft.fft(amplitude_data)  # Perform FFT on the amplitude data
fft_freqs = np.fft.fftfreq(num_samples, 1 / sample_rate)  # Frequency bins for the FFT output
fft_magnitude = np.abs(fft_data)  # Magnitude of the FFT results

# Plot the FFT (Frequency vs Magnitude)
plt.subplot(3, 1, 2)
plt.plot(fft_freqs[:num_samples // 2], fft_magnitude[:num_samples // 2])  # Only plot the positive frequencies
plt.title('FFT of Signal')
plt.xlabel('Frequency [Hz]')
plt.ylabel('Magnitude')
plt.grid(True)

# Convert to numpy array
amplitude_data = np.array(volts)

# Perform FFT
absFreqSpectrum = np.abs(fft(amplitude_data))

# Frequency axis
timeX = np.linspace(0, sample_rate / 2, len(amplitude_data) // 2)  

plt.subplot(3, 1, 3)
plt.plot(timeX, absFreqSpectrum[:len(amplitude_data) // 2])
plt.xlabel("Frequency [Hz]")
plt.ylabel("|X(n)|")
plt.title("FFT Spectrum")
plt.grid(True)
plt.tight_layout()
plt.show()

# Show the plots
plt.tight_layout()
plt.show()
