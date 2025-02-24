import time
import numpy as np
import pigpio
from led_control import Strip
from songs import Songs
from state import NoteStateMachine
import copy
import scipy.fftpack

# General settings
SAMPLE_FREQ = 20000  # Sample frequency for ADC
WINDOW_SIZE = 8192  # FFT window size
WINDOW_STEP = 12000  # Step size of window (can be adjusted)
NUM_HPS = 5  # Max number of harmonic product spectrums
POWER_THRESH = 18000  # Threshold for signal power
CONCERT_PITCH = 440  # Defining A4
WHITE_NOISE_THRESH = 0.2
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]
ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]

# Initialize the components
strip = Strip()
songs = Songs("songs.json", 0.7, strip)
state_machine = NoteStateMachine(songs)
played_notes = []

# Initialize pigpio and configure SPI for ADC
pi = pigpio.pi()
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI bus (0 or 1)
SPI_SPEED = 500000  # 500 kHz SPI clock
pi.spi_open(SPI_BUS, SPI_SPEED, 0)

# ADC reading function
def read_adc(channel):
    """Reads a 12-bit value from MCP3208 ADC"""
    if channel < 0 or channel > 7:
        return -1
    cmd = [1, (8 + channel) << 4, 0]
    count, data = pi.spi_xfer(SPI_BUS, cmd)
    if count == 3:
        return ((data[1] & 0x0F) << 8) | data[2]
    return -1

# Function to find the closest note for a given frequency
def find_closest_note(pitch):
    """Find the closest note for a given pitch"""
    i = int(np.round(np.log2(pitch / CONCERT_PITCH) * 12))
    closest_note = ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)
    closest_pitch = CONCERT_PITCH * 2 ** (i / 12)
    return closest_note, closest_pitch

# Calculate the frequency of the dominant peak using FFT
def get_frequency(samples):
    """Compute dominant frequency using FFT"""
    fft_result = np.fft.rfft(samples)
    fft_freqs = np.fft.rfftfreq(len(samples), d=1 / SAMPLE_FREQ)
    magnitude = np.abs(fft_result)
    magnitude[0] = 0  # Ignore DC component
    return fft_freqs[np.argmax(magnitude)]

# Calculate the power of the signal from ADC samples
def calculate_signal_power(adc_samples):
    """Calculate the power of the signal from ADC samples"""
    return np.mean(np.square(adc_samples))

# Main loop to collect ADC samples and process the frequency
def process_adc_data():
    samples = np.zeros(WINDOW_SIZE)
    last_time = time.time()
    
    # Start the main processing loop
    while not songs.FINISHED:
        # Shift old samples to keep 50% overlap
        samples[:-WINDOW_STEP] = samples[WINDOW_STEP:]

        # Read new samples to fill the rest of the buffer
        for i in range(WINDOW_STEP, WINDOW_SIZE):
            samples[i] = read_adc(0)  # Assuming channel 0
            time.sleep(1 / SAMPLE_FREQ)

        # Calculate signal power and frequency
        power = calculate_signal_power(samples)
        if power < POWER_THRESH:
            print("Signal power too low")
            continue

        dominant_frequency = get_frequency(samples)
        print(f"Dominant Frequency: {dominant_frequency:.2f} Hz")

        # Determine the closest note
        closest_note, closest_pitch = find_closest_note(dominant_frequency)
        print(f"Closest Note: {closest_note}, Frequency: {closest_pitch:.2f} Hz")
        
        # Handle note input
        state_machine.handle_input(closest_note)

        # Sleep to maintain sampling rate
        elapsed = time.time() - last_time
        sleep_time = (1 / SAMPLE_FREQ) - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)
        last_time = time.time()

# Run the process
if __name__ == '__main__':
    try:
        process_adc_data()
    except KeyboardInterrupt:
        print("Program interrupted")
    finally:
        pi.stop()  # Clean up pigpio connection
