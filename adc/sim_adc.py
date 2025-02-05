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
SPI_CS = 8   # Chip select GPIO pin (adjust as needed)
SAMPLE_FREQ = 50000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
POWER_THRESH = 9e-4  # Tuning is activated if the signal power exceeds this threshold
NOISE_LEVEL = 0.02  # Noise level (0 to 1, where 1 is full scale)

pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)

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
    print("Starting ADC simulation...")
    samples = []
    freq = 261.63  # Frequency of Middle C (261.63 Hz)
    f = 0
    while f <2:
        # Simulate an ADC reading (for testing with sine wave of Middle C)
        adc_value = read_adc(channel=0)  # Read from ADC channel 0 (you can change to the channel you need)
        voltage = convert_to_voltage(adc_value)  # Convert raw ADC value to voltage
        # print(f"ADC Value: {adc_value}, Voltage: {voltage:.3f} V")
        
        samples.append(voltage)

        if len(samples) >= WINDOW_SIZE:
            plt.figure(figsize=(10, 6))
            plt.plot(samples[:100])  # Show first 100 samples
            plt.title("First 100 ADC Values for Piano Middle C with Harmonics, ADSR Envelope, and Noise")
            plt.xlabel("Sample Number")
            plt.ylabel("ADC Value")
            plt.grid(True)
            plt.show()
            # Get the frequency of the signal in the collected samples
            dominant_frequency = get_frequency(samples)
            real_f = dominant_frequency / 8.3
            power = calculate_signal_power(samples)
            print(f"Signal Power: {power:.6f}")
            if power > POWER_THRESH:
                print(f"Dominant frequency: {dominant_frequency:.2f} Hz")
                print(f" real_f: {real_f:.2f} Hz")

            # Clear the sample window to collect the next set of data
            samples = []
            f +=1

        time.sleep(1 / SAMPLE_FREQ)  # Ensure the sampling rate is consistent

except KeyboardInterrupt:
    print("Program interrupted")

finally:
    pi.stop()  # Clean up pigpio connection
