import pigpio
import time
import numpy as np
import matplotlib.pyplot as plt
from scipy.fftpack import fft
import scipy.fftpack

# SPI parameters
SPI_CHANNEL = 0  # SPI channel (0 or 1)
SPI_SPEED = 500000  # SPI speed (Hz)
SPI_MODE = 0  # SPI mode (0, 1, 2, or 3)
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
WINDOW_SIZE = 2048 # window size of the DFT in samples

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


def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2 ** BIT_DEPTH - 1))

# Sampling parameters
sample_rate = 48000  # Number of samples per second (adjust this depending on your ADC)
duration = 0.01  # Duration to capture data for FFT analysis
num_samples = int(sample_rate * duration)

# Function to calculate the dominant frequency from the FFT data
def calculate_dominant_frequency(amplitude_data, sample_rate):
    fft_data = np.fft.fft(amplitude_data)
    fft_freqs = np.fft.fftfreq(len(fft_data), 1 / sample_rate)
    fft_magnitude = np.abs(fft_data)
    
    # Find the peak in the FFT magnitude
    peak_index = np.argmax(fft_magnitude[:len(fft_magnitude) // 2])
    dominant_frequency = fft_freqs[peak_index]
    
    return dominant_frequency


def get_frequency(samples):
    """Get the dominant frequency from ADC samples using FFT"""
    # Perform FFT
    fft_result = fft(samples)
    fft_freqs = scipy.fftpack.fftfreq(len(samples), d=1/sample_rate)

    # Get the magnitude of the FFT result
    magnitude = np.abs(fft_result)
    magnitude[0] = 0

    # plt.figure(figsize=(10, 6))
    # plt.plot(fft_freqs[:len(samples)//2], magnitude[:len(samples)//2])
    # plt.title('Magnitude Spectrum')
    # plt.xlabel('Frequency (Hz)')
    # plt.ylabel('Magnitude')
    # plt.grid(True)
    # plt.show()

    # Find the index of the peak frequency
    peak_index = np.argmax(magnitude)
    peak_freq = np.abs(fft_freqs[peak_index])

    # Since the FFT gives both positive and negative frequencies, ensure we use the positive part
    if peak_freq > sample_rate / 2:
        peak_freq -= sample_rate

    return peak_freq
try:
        
    amplitude_data = []
    samples = []
    while True:
        # Collect samples


        adc_value = read_adc(1)  # Read from channel 0 (you can change the channel)
        voltage = convert_to_voltage(adc_value)  # Convert raw ADC value to voltage
        samples.append(adc_value)
        print (len(samples), WINDOW_SIZE)
        if len(samples) >= WINDOW_SIZE:
            dominant_frequency = get_frequency(samples)
            samples = []
            print("dom")
            print (dominant_frequency)
        time.sleep(1 / sample_rate)  # Wait for the next sample
        
        # # Calculate the dominant frequency
        # dominant_frequency = calculate_dominant_frequency(amplitude_data, sample_rate)
        # print(f"Dominant Frequency: {dominant_frequency:.2f} Hz")
        
       
        
except KeyboardInterrupt:
    print("Terminated by user")

finally:
    # Close the SPI connection and pigpio
    pi.spi_close(spi_handle)
    pi.stop()