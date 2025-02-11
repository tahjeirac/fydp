import pigpio
import time
import numpy as np
import scipy.fftpack
import time
import matplotlib.pyplot as plt


# Set up pigpio and configure SPI settings
pi = pigpio.pi()  # Create an instance of pigpio
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI bus (0 or 1)
SPI_CS = 8   # Chip select GPIO pin (adjust as needed)
SAMPLE_FREQ = 50000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
POWER_THRESH = 9e-4 # tuning is activated if the signal power exceeds this threshold

# Initialize SPI communication
pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)

def read_adc(channel):
    """Reads a value from the ADC using SPI with DMA"""
    # ADC command for MCP3208 (12-bit ADC)
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    
    # Send the command to the ADC
    result = pi.spi_xfer(SPI_BUS, command)
    
    # Convert the result to 12-bit value
    value = (result[1][1] & 0x0F) << 8 | result[1][2]
    
    return value

def ConvertToVoltage(value, bitdepth, vref):
    return vref * (value / (2 ** bitdepth - 1))
# Example: Read ADC value from channel 0

def convert_to_voltage(adc_value):
    """Convert ADC value to voltage"""
    return VREF * (adc_value / (2 ** BIT_DEPTH - 1))

def ConvertToDB(value, bitdepth):
    return 20 * np.log10(value / (2 ** bitdepth - 1))
def get_frequency(samples):
    """Get the dominant frequency from ADC samples using FFT"""
    # Perform FFT
    fft_result = scipy.fftpack.fft(samples)
    fft_freqs = scipy.fftpack.fftfreq(len(samples), d=1/SAMPLE_FREQ)

    # Get the magnitude of the FFT result
    magnitude = np.abs(fft_result)
    magnitude[0] = 0

    plt.figure(figsize=(10, 6))
    plt.plot(fft_freqs[:len(samples)//2], magnitude[:len(samples)//2])
    plt.title('Magnitude Spectrum')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Magnitude')
    plt.grid(True)
    plt.show()
   # print(f"Magnitude (First 10 bins): {magnitude[:10]}")
   # print(f"Frequency bins (First 10): {fft_freqs[:10]}")

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
    samples = []
    freq = 0
    while freq < 3:
        adc_value = read_adc(0)
        print(f"ADC Value: {adc_value}")
        samples.append(adc_value*8.3)

        if len(samples) >= WINDOW_SIZE:
            # Get the frequency of the signal in the collected samples
            dominant_frequency = get_frequency(samples)
            real_f = dominant_frequency/8.3
            power = calculate_signal_power(samples)
            print(f"Signal Power: {power:.6f}")
            if power > POWER_THRESH:

                print(f"Dominant frequency: {dominant_frequency:.2f} Hz")
                print(f" real_f: {real_f:.2f} Hz")

            # Clear the sample window to collect the next set of data
            samples = []
            freq += 1

        time.sleep(1 / SAMPLE_FREQ)  # Ensure the sampling rate is consistent


except KeyboardInterrupt:
    print("Program interrupted")

finally:
    pi.spi_close(SPI_BUS)
    pi.stop()
