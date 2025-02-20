import time
import numpy as np
import pigpio

# Set up pigpio and configure SPI settings
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI bus (0 or 1)
SAMPLE_FREQ = 20000  # 20 kHz sampling rate
WINDOW_SIZE = 8192   # FFT window size
OVERLAP = WINDOW_SIZE // 2  # 50% overlap (4096 samples)
POWER_THRESH = 18000
SPI_SPEED = 500000  # 500 kHz SPI clock

pi.spi_open(SPI_BUS, SPI_SPEED, 0)

samples = np.zeros(WINDOW_SIZE)

def read_adc(channel):
    """Reads a 12-bit value from MCP3208 ADC"""
    if channel < 0 or channel > 7:
        return -1
    cmd = [1, (8 + channel) << 4, 0]
    count, data = pi.spi_xfer(SPI_BUS, cmd)
    if count == 3:
        return ((data[1] & 0x0F) << 8) | data[2]
    return -1

def get_frequency(samples):
    """Compute dominant frequency using FFT"""
    fft_result = np.fft.rfft(samples)
    fft_freqs = np.fft.rfftfreq(len(samples), d=1/SAMPLE_FREQ)
    magnitude = np.abs(fft_result)
    magnitude[0] = 0  # Ignore DC component
    return fft_freqs[np.argmax(magnitude)]

def calculate_signal_power(adc_samples):
    """Calculate the power of the signal from ADC samples"""
    return np.mean(np.square(adc_samples))

try:
    print("Starting ADC...")
    last_time = time.time()
    
    while True:
        # Shift old samples to keep OVERLAP samples
        samples[:-OVERLAP] = samples[OVERLAP:]
        
        # Read new samples to fill the rest of the buffer
        for i in range(OVERLAP, WINDOW_SIZE):
            samples[i] = read_adc(0)
            time.sleep(1 / SAMPLE_FREQ)  # Maintain sample rate
        
        power = calculate_signal_power(samples)
        print (power)
        dominant_frequency = get_frequency(samples)
        print(f"Dominant Frequency: {dominant_frequency:.2f} Hz")
        
        # if power > POWER_THRESH:
        #     dominant_frequency = get_frequency(samples)
        #     print(f"Dominant Frequency: {dominant_frequency:.2f} Hz")
        
        # elapsed = time.time() - last_time
        # sleep_time = (1 / SAMPLE_FREQ) - elapsed
        # if sleep_time > 0:
        #     time.sleep(sleep_time)
        # last_time = time.time()

except KeyboardInterrupt:
    print("Program interrupted")

finally:
    pi.stop()  # Clean up pigpio connection
