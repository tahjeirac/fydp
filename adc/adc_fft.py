import spidev
import time
import numpy as np
import scipy.fftpack
import os

# Setup SPI bus for ADC
spi = spidev.SpiDev()
spi.open(0, 0)  # SPI bus 0, chip select 0
spi.max_speed_hz = 1000000

# Define function to read ADC data
def ReadChannel3208(channel):
    adc = spi.xfer2([6 | (channel >> 2), channel << 6, 0])  # MCP3208 command format
    data = ((adc[1] & 15) << 8) + adc[2]
    return data

# Constants
SAMPLE_FREQ = 48000  # Sample frequency in Hz (adjust as needed)
WINDOW_SIZE = 1024  # FFT window size
HANN_WINDOW = np.hanning(WINDOW_SIZE)
DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE  # Frequency resolution

# Note detection functions
ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]
CONCERT_PITCH = 440  # A4 frequency
NoteConversion = {'C4': 7, 'B4': 1, 'A4': 2, 'G4': 3, 'F4': 4, 'E4': 5, 'D4': 6}

def find_closest_note(pitch):
    i = int(np.round(np.log2(pitch / CONCERT_PITCH) * 12))
    closest_note = ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)
    closest_pitch = CONCERT_PITCH * 2 ** (i / 12)
    return closest_note, closest_pitch

# Octave bands and power threshold
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]
WHITE_NOISE_THRESH = 0.2
POWER_THRESH = 1e-6  # Signal power threshold

# Setup a buffer for ADC data
adc_buffer = np.zeros(WINDOW_SIZE)

def process_adc_data():
    """
    Function to process ADC data, perform FFT, and detect the closest note.
    """
    global adc_buffer
    adc_data = ReadChannel3208(1)  # Read from channel 1 of the ADC
    adc_buffer = np.append(adc_buffer[1:], adc_data)  # Shift buffer and add new data

    # Apply Hanning window to the buffer to reduce spectral leakage
    hann_samples = adc_buffer * HANN_WINDOW

    # Perform FFT to get frequency spectrum
    magnitude_spec = np.abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples) // 2])

    # Signal power calculation (using L2 norm of samples)
    signal_power = (np.linalg.norm(adc_buffer, ord=2)**2) / len(adc_buffer)
    print (signal_power)
    if signal_power < POWER_THRESH:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("Signal too weak, no note detected")
        return

    # # Calculate average energy per frequency for the octave bands
    # for j in range(len(OCTAVE_BANDS)-1):
    #     ind_start = int(OCTAVE_BANDS[j] / DELTA_FREQ)
    #     ind_end = int(OCTAVE_BANDS[j+1] / DELTA_FREQ)
    #     ind_end = ind_end if len(magnitude_spec) > ind_end else len(magnitude_spec)
    #     avg_energy_per_freq = (np.linalg.norm(magnitude_spec[ind_start:ind_end], ord=2)**2) / (ind_end - ind_start)
    #     avg_energy_per_freq = avg_energy_per_freq**0.5
    #     for i in range(ind_start, ind_end):
    #         magnitude_spec[i] = magnitude_spec[i] if magnitude_spec[i] > WHITE_NOISE_THRESH * avg_energy_per_freq else 0

    # # Harmonic Product Spectrum (HPS)
    # num_hps = 5  # Max number of harmonic products to use
    # mag_spec_ipol = np.interp(np.arange(0, len(magnitude_spec), 1 / num_hps), np.arange(0, len(magnitude_spec)), magnitude_spec)
    # mag_spec_ipol = mag_spec_ipol / np.linalg.norm(mag_spec_ipol, ord=2)  # Normalize

    # hps_spec = mag_spec_ipol.copy()

    # # Calculate the HPS
    # for i in range(num_hps):
    #     tmp_hps_spec = np.multiply(hps_spec[:int(np.ceil(len(mag_spec_ipol) / (i + 1)))], mag_spec_ipol[::(i + 1)])
    #     if not any(tmp_hps_spec):
    #         break
    #     hps_spec = tmp_hps_spec

    # # Find the frequency with the highest power in the HPS
    # max_ind = np.argmax(hps_spec)
    # max_freq = max_ind * (SAMPLE_FREQ / WINDOW_SIZE) / num_hps

    # # Get the closest note and pitch
    # closest_note, closest_pitch = find_closest_note(max_freq)

    # # Output the closest note and frequency
    # print(f"Detected Note: {closest_note} at {max_freq:.1f} Hz (Pitch: {closest_pitch:.1f} Hz)")

# Main loop to continuously process ADC data
if __name__ == "__main__":
    while True:
        process_adc_data()
        time.sleep(0.01)  # Adjust delay for your application (e.g., 10 ms)
