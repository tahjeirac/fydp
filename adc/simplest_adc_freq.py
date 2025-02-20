import time
import numpy as np
import scipy.fftpack
import pigpio
import matplotlib.pyplot as plt

# Set up pigpio and configure SPI settings
pi = pigpio.pi()  # Create an instance of pigpio
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI bus (0 or 1)
SAMPLE_FREQ = 20000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window
POWER_THRESH = 18000 # tuning is activated if the signal power exceeds this threshold

SPI_SPEED = 500000  # 500 kHz SPI clock
SAMPLE_RATE = 20000  # Target 20 kHz

pi.spi_open(SPI_BUS, SPI_SPEED, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)

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

def get_frequency(samples):
    """Get the dominant frequency from ADC samples using FFT"""
    # Perform FFT
    fft_result = scipy.fftpack.fft(samples)
    fft_freqs = scipy.fftpack.fftfreq(len(samples), d=1/SAMPLE_FREQ)

    # Get the magnitude of the FFT result
    magnitude = np.abs(fft_result)
    magnitude[0] = 0

    # Find the index of the peak frequency
    peak_index = np.argmax(magnitude)
    peak_freq = np.abs(fft_freqs[peak_index])

    # Since the FFT gives both positive and negative frequencies, ensure we use the positive part
    if peak_freq > SAMPLE_FREQ / 2:
        peak_freq -= SAMPLE_FREQ

    return peak_freq

def calculate_signal_power(adc_samples):
    """Calculate the power of the signal from ADC samples"""
    # Square the ADC values and take the average (mean)
    power = np.mean(np.square(adc_samples))
    return power

try:
    print("Starting ADC...")
    samples = []
    while True:
        adc_value = read_adc(channel=0)  # Read from ADC channel 0 (you can change to the channel you need)
        # print(f"ADC Value: {adc_value}, Voltage: {voltage:.3f} V")
        
        samples.append(adc_value)

        if len(samples) >= WINDOW_SIZE:
            power = calculate_signal_power(samples)
            print (power)
            if power > POWER_THRESH:
                dominant_frequency = get_frequency(samples)
                dominant_frequency_scale = dominant_frequency/72.5

                print(f"Dominant frequency: {dominant_frequency:.2f} Hz")
                print(f"Dominant frequency real: {dominant_frequency_scale:.2f} Hz")
            # Clear the sample window to collect the next set of data
            samples = []

        time.sleep(1 / SAMPLE_FREQ)  # Ensure the sampling rate is consistent

except KeyboardInterrupt:
    print("Program interrupted")

finally:
    pi.stop()  # Clean up pigpio connection
