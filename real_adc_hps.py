import time
import numpy as np
import scipy.fftpack
import matplotlib.pyplot as plt
import os
import copy
import pigpio

pi = pigpio.pi()  # Create an instance of pigpio
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()


# Parameters and constants
SPI_BUS = 0  # SPI bus (0 or 1)

pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)

SAMPLE_FREQ = 50000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
POWER_THRESH = 9e-4 # tuning is activated if the signal power exceeds this threshold
NOISE_LEVEL = 0.02  # Noise level (0 to 1, where 1 is full scale)
HARMONIC_COUNT = 5  # Number of harmonics to include
ADSR_ATTACK = 0.1  # Attack time in seconds
ADSR_SUSTAIN = 0.7  # Sustain level (0-1)
ADSR_RELEASE = 0.1  # Release time in seconds
CONCERT_PITCH = 440  # Concert pitch A4 frequency in Hz
WHITE_NOISE_THRESH = 0.2  # everything under WHITE_NOISE_THRESH*avg_energy_per_freq is cut off
NUM_HPS = 5  # max number of harmonic product spectrums
WINDOW_T_LEN = WINDOW_SIZE / SAMPLE_FREQ  # length of the window in seconds
SAMPLE_T_LENGTH = 1 / SAMPLE_FREQ  # length between two samples in seconds
DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE  # frequency step width of the interpolated DFT
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]
ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]
NoteConversion = {'C4':7, 'B4':1, 'A4':2, 'G4': 3, 'F4':4, 'E4': 5, 'D4':6}

HANN_WINDOW = np.hanning(WINDOW_SIZE)

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

# Function to generate ADSR envelope
def generate_adsr_envelope(duration, attack, sustain, release, sample_rate):
    attack_samples = int(attack * sample_rate)
    sustain_samples = int(sustain * sample_rate)
    release_samples = int(release * sample_rate)
    envelope = np.zeros(int(duration * sample_rate))
    
    envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
    envelope[attack_samples:attack_samples+sustain_samples] = 1.0
    envelope[-release_samples:] = np.linspace(1, 0, release_samples)
    
    return envelope

# Get the closest note from frequency
def find_closest_note(pitch):
    i = int(np.round(np.log2(pitch/CONCERT_PITCH)*12))
    closest_note = ALL_NOTES[i%12] + str(4 + (i + 9) // 12)
    closest_pitch = CONCERT_PITCH*2**(i/12)
    return closest_note, closest_pitch

# Callback function for processing samples
def callback(indata):
    """Callback function of the InputStream method."""
    if not hasattr(callback, "window_samples"):
        callback.window_samples = np.zeros(WINDOW_SIZE)  # Initialize window_samples
    if not hasattr(callback, "noteBuffer"):
        callback.noteBuffer = ["1", "2"]

    if any(indata):
        callback.window_samples = np.concatenate((callback.window_samples, indata))  # append new samples
        callback.window_samples = callback.window_samples[len(indata):]  # remove old samples

        signal_power = np.linalg.norm(callback.window_samples)**2 / len(callback.window_samples)
        
        if signal_power < POWER_THRESH:
            os.system('cls' if os.name=='nt' else 'clear')
            print("Closest note: ...")
            return

        # Multiply with Hann window to avoid spectral leakage
        hann_samples = callback.window_samples * HANN_WINDOW
        magnitude_spec = abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples)//2])

        # Suppress mains hum
        for i in range(int(62/DELTA_FREQ)):
            magnitude_spec[i] = 0

        # Calculate average energy per frequency for octave bands and suppress
        for j in range(len(OCTAVE_BANDS)-1):
            ind_start = int(OCTAVE_BANDS[j]/DELTA_FREQ)
            ind_end = int(OCTAVE_BANDS[j+1]/DELTA_FREQ) -1
            ind_end = min(ind_end, len(magnitude_spec) - 1)
            avg_energy_per_freq = np.sqrt(np.mean(np.square(magnitude_spec[ind_start:ind_end])))
            for i in range(ind_start, ind_end):
                magnitude_spec[i] = magnitude_spec[i] if magnitude_spec[i] > WHITE_NOISE_THRESH * avg_energy_per_freq else 0

        # Interpolate spectrum
        mag_spec_ipol = np.interp(np.arange(0, len(magnitude_spec), 1/NUM_HPS), np.arange(0, len(magnitude_spec)), magnitude_spec)
        mag_spec_ipol = mag_spec_ipol / np.linalg.norm(mag_spec_ipol)  # Normalize

        # Calculate Harmonic Product Spectrum (HPS)
        hps_spec = mag_spec_ipol.copy()
        for i in range(NUM_HPS):
            tmp_hps_spec = np.multiply(hps_spec[:int(np.ceil(len(mag_spec_ipol)/(i+1)))], mag_spec_ipol[::(i+1)])
            if not any(tmp_hps_spec):
                break
            hps_spec = tmp_hps_spec

        max_ind = np.argmax(hps_spec)
        max_freq = max_ind * (SAMPLE_FREQ / WINDOW_SIZE) / NUM_HPS

        closest_note, closest_pitch = find_closest_note(max_freq)
        callback.noteBuffer.insert(0, closest_note)  # Insert into noteBuffer
        callback.noteBuffer.pop()

        os.system('cls' if os.name == 'nt' else 'clear')
        if callback.noteBuffer.count(callback.noteBuffer[0]) == len(callback.noteBuffer):
            print(f"Closest note: {closest_note} {max_freq:.2f} Hz / {closest_pitch:.2f} Hz")
        else:
            print(f"Closest note: ...")

# Simulate the ADC signal for testing
try:
    print("Starting ADC")
    
    window = []

    while True:
        adc_value = read_adc(channel=0)  # Read from ADC channel 0 (you can change to the channel you need)

        # Feed the ADC values to the callback in windows
        window.append(adc_value)
        if len(window) == WINDOW_SIZE:
                # plt.figure(figsize=(10, 6))
                # plt.plot(window)  # Show first 100 samples
                # plt.title("window samples")
                # plt.xlabel("Sample Number")
                # plt.ylabel("ADC Value")
                # plt.grid(True)
                # plt.show()
                callback(np.array(window))  # Call callback once the window is filled
                window = []  # Reset window for next batch of samples
        time.sleep(1 / SAMPLE_FREQ)  # Maintain sample rate

except KeyboardInterrupt:
    print("Program interrupted")
