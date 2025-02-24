import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft

# Amplitude data
with open("amplitude_data.txt", "r") as file:
    amplitude_data = [float(line.strip()) for line in file]

print(amplitude_data)  # List of numbers
sample_rate = 48000

# Fourier Transform
amplitude_data = np.array(amplitude_data)
timeX = np.linspace(0, sample_rate / 2, len(amplitude_data) // 2)  

# Perform FFT
absFreqSpectrum = np.abs(fft(amplitude_data))
fft_data = np.fft.fft(amplitude_data)
fft_result = np.fft.fft(amplitude_data)
frequencies = np.fft.fftfreq(len(fft_result), 1/sample_rate)

# Magnitude calculation
magnitude = np.abs(fft_result)

# Plot
plt.figure(figsize=(10, 6))

# Record data for 2 seconds
duration = 0.005  # Record for 2 seconds
sample_rate = 48000  # Number of samples per second (adjust this depending on your ADC)
num_samples = int(duration * sample_rate)
time_data = np.linspace(0, duration, num_samples)

plt.figure(figsize=(10, 6))
plt.plot(time_data, amplitude_data)
plt.title('Amplitude vs Time')
plt.xlabel('Time [s]')
plt.ylabel('Amplitude [V]')
plt.grid(True)

# plt.plot(timeX, absFreqSpectrum[:len(amplitude_data) // 2])
# plt.xlabel("Frequency [Hz]")
# plt.ylabel("|X(n)|")
# plt.title("FFT Spectrum")
# plt.grid(True)
# plt.grid(True)
plt.show()
