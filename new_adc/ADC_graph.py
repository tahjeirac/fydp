import pigpio
import time
import numpy as np
import matplotlib.pyplot as plt

# SPI parameters
SPI_CHANNEL = 0  # SPI channel (0 or 1)
SPI_SPEED = 1000000  # SPI speed (Hz)
SPI_MODE = 0  # SPI mode (0, 1, 2, or 3)

# Setup pigpio library
pi = pigpio.pi()

if not pi.connected:
    print("Failed to connect to pigpio daemon")
    exit()

# Initialize the SPI
spi_handle = pi.spi_open(SPI_CHANNEL, SPI_SPEED, SPI_MODE)

# Define the function to read from the ADC
def read_adc(channel):
    """Read data from an ADC channel using SPI."""
    # Send the start byte (1) + control bits for the channel to read
    # For MCP3208, channel bits are set as follows:
    # - Start bit: 1
    # - SGL/Diff bit: 1 (single-ended mode)
    # - D2, D1, D0 bits for the channel number (0-7)
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    result = pi.spi_xfer(spi_handle, command)
    adc_value = ((result[1][1] & 0x0F) << 8) | result[1][2]
    return adc_value

# Record data for 2 seconds
duration = 0.005  # Record for 2 seconds
sample_rate = 48000  # Number of samples per second (adjust this depending on your ADC)
num_samples = int(duration * sample_rate)

# Store the readings
time_data = np.linspace(0, duration, num_samples)
amplitude_data = []

# Read ADC data and store amplitude values
start_time = time.time()
while len(amplitude_data) < num_samples:
    adc_value = read_adc(1)  # Read from channel 0 (you can change the channel)
    # Normalize the ADC value to a range (e.g., 0-3.3V for a 3.3V reference voltage)
    amplitude = (adc_value / 4095.0) * 3.3  # Assuming 12-bit ADC and 3.3V reference
    amplitude_data.append(amplitude)
    time.sleep(1 / sample_rate)  # Wait for the next sample

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

fft_values = np.fft.fftshift(np.fft.fft(amplitude_data))
magnitude = np.fft.fftshift(np.abs(fft_values))
frequencies = np.fft.fftshift(np.fft.fftfreq(num_samples, 1 / sample_rate))

plt.subplot(3, 1, 3)
plt.plot(frequencies, magnitude, 'b-')
plt.title("Frequency Domain: Magnitude Spectrum")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.grid(True)
plt.xlim(0, sample_rate / 2)  # Limit to Nyquist frequency
plt.tight_layout()
plt.show()

# Show the plots
plt.tight_layout()
plt.show()

# Close the SPI connection and pigpio
pi.spi_close(SPI_CHANNEL)
pi.stop()
