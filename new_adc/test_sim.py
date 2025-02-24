import copy
import os
import numpy as np
import scipy.fftpack
import time
import argparse
import json
import wave
import spidev  # For communicating with the ADC


# General settings that can be changed by the user
SAMPLE_FREQ = 48000  # Sample frequency in Hz (how often we sample the ADC)
WINDOW_SIZE = 48000  # Window size of the DFT (Discrete Fourier Transform) in samples
WINDOW_STEP = 12000  # Step size of the window (how much the window moves forward each time)
NUM_HPS = 5  # Max number of harmonic product spectrums for pitch detection
POWER_THRESH = 1e-6  # The signal power threshold below which tuning is deactivated
CONCERT_PITCH = 440  # The reference pitch A4, which corresponds to 440 Hz
WHITE_NOISE_THRESH = 0.2  # Threshold for white noise suppression, applied to average energy per frequency

# Derived settings based on the general settings
WINDOW_T_LEN = WINDOW_SIZE / SAMPLE_FREQ  # Length of the window in seconds
SAMPLE_T_LENGTH = 1 / SAMPLE_FREQ  # Length between two samples in seconds
DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE  # Frequency step width of the interpolated DFT
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]  # Frequency bands for octave calculation

MATCH_DELAY = 0.7  # Delay between allowed matches, in seconds (prevents rapid repeats)
ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]  # Notes used for conversion

# Mapping for note conversion (C4 = middle C)
NoteConversion = {'C4': 7, 'B4': 1, 'A4': 2, 'G4': 3, 'F4': 4, 'E4': 5, 'D4': 6}

# Instantiate objects for handling song playback, LED control, and note state machine


# SPI configuration for ADC
spi = spidev.SpiDev()
spi.open(0, 0)  # Open SPI port 0, device 0
spi.max_speed_hz = 50000  # Set the SPI speed (can be adjusted based on your ADC specs)

def read_adc(channel):
    """
    Reads data from the ADC via SPI.
    Parameters:
        channel (int): The ADC channel from which to read data.
    Returns:
        int: The ADC value (10-bit).
    """
    # SPI command to read from the ADC channel
    adc_data = spi.xfer2([1, (8 + channel) << 4, 0])  # Send the command and receive the response
    return ((adc_data[1] & 3) << 8) + adc_data[2]  # Extract the 10-bit value from the response

def find_closest_note(pitch):
    """
    This function finds the closest note for a given pitch in Hz.
    Parameters:
        pitch (float): The pitch in Hz.
    Returns:
        closest_note (str): The closest musical note (e.g., 'A4', 'G#4', etc.).
        closest_pitch (float): The pitch of the closest note in Hz.
    """
    i = int(np.round(np.log2(pitch / CONCERT_PITCH) * 12))  # Calculate the note index
    closest_note = ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)  # Determine the note (e.g., 'A4', 'C#5')
    closest_pitch = CONCERT_PITCH * 2 ** (i / 12)  # Calculate the exact pitch in Hz
    return closest_note, closest_pitch

HANN_WINDOW = np.hanning(WINDOW_SIZE)  # Apply a Hanning window to reduce spectral leakage

def process_audio_samples():
    """
    This function processes the ADC samples, applies a window, performs an FFT, 
    and detects the pitch of the signal.
    """
    # Define static variables for the callback (this ensures they are initialized only once)
    if not hasattr(process_audio_samples, "window_samples"):
        process_audio_samples.window_samples = [0 for _ in range(WINDOW_SIZE)]

    if not hasattr(process_audio_samples, "noteBuffer"):
        process_audio_samples.noteBuffer = ["1", "2"]

    # Collect the samples from the ADC (in this example, using channel 0)
    adc_samples = [read_adc(channel=0) for _ in range(WINDOW_STEP)]  # Collect WINDOW_STEP worth of data

    # Update the window samples buffer by concatenating new samples and removing the oldest ones
    process_audio_samples.window_samples = np.concatenate((process_audio_samples.window_samples, adc_samples))
    process_audio_samples.window_samples = process_audio_samples.window_samples[len(adc_samples):]

    # Skip if the signal power is too low to detect a note
    signal_power = (np.linalg.norm(process_audio_samples.window_samples, ord=2) ** 2) / len(process_audio_samples.window_samples)
    print (signal_power)
    # if signal_power < POWER_THRESH:
    #     os.system('cls' if os.name == 'nt' else 'clear')  # Clear screen for better readability
    #     print("Closest note: ...")
    #     return

    # Apply the Hanning window to avoid spectral leakage and compute the FFT
    hann_samples = process_audio_samples.window_samples * HANN_WINDOW
    magnitude_spec = abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples) // 2])

    # Suppress mains hum by setting everything below 62Hz to zero
    for i in range(int(62 / DELTA_FREQ)):
        magnitude_spec[i] = 0

    # Suppress white noise by checking average energy in octave bands
    for j in range(len(OCTAVE_BANDS) - 1):
        ind_start = int(OCTAVE_BANDS[j] / DELTA_FREQ)
        ind_end = int(OCTAVE_BANDS[j + 1] / DELTA_FREQ)
        avg_energy_per_freq = np.linalg.norm(magnitude_spec[ind_start:ind_end], ord=2) / (ind_end - ind_start)
        avg_energy_per_freq = avg_energy_per_freq ** 0.5
        for i in range(ind_start, ind_end):
            magnitude_spec[i] = magnitude_spec[i] if magnitude_spec[i] > WHITE_NOISE_THRESH * avg_energy_per_freq else 0

    # Interpolate the spectrum for better frequency resolution
    mag_spec_ipol = np.interp(np.arange(0, len(magnitude_spec), 1 / NUM_HPS), np.arange(0, len(magnitude_spec)), magnitude_spec)
    mag_spec_ipol = mag_spec_ipol / np.linalg.norm(mag_spec_ipol, ord=2)  # Normalize the spectrum

    hps_spec = copy.deepcopy(mag_spec_ipol)

    # Calculate the Harmonic Product Spectrum (HPS) by multiplying frequency bins
    for i in range(NUM_HPS):
        tmp_hps_spec = np.multiply(hps_spec[:int(np.ceil(len(mag_spec_ipol) / (i + 1)))], mag_spec_ipol[::(i + 1)])
        if not any(tmp_hps_spec):
            break
        hps_spec = tmp_hps_spec

    # Find the peak frequency in the HPS
    max_ind = np.argmax(hps_spec)
    max_freq = max_ind * (SAMPLE_FREQ / WINDOW_SIZE) / NUM_HPS

    # Find the closest note and pitch corresponding to the detected frequency
    closest_note, closest_pitch = find_closest_note(max_freq)
    max_freq = round(max_freq, 1)
    print (max_freq)
    closest_pitch = round(closest_pitch, 1)

    # Update the note buffer (ring buffer) and clear the console
    process_audio_samples.noteBuffer.insert(0, closest_note)
    process_audio_samples.noteBuffer.pop()

    os.system('cls' if os.name == 'nt' else 'clear')
    if process_audio_samples.noteBuffer.count(process_audio_samples.noteBuffer[0]) == len(process_audio_samples.noteBuffer):
        print(f"Closest note: {closest_note} {max_freq}/{closest_pitch}")
    else:
        print("Closest note: ...")

def main():
    """
    Main function to initialize and run the script.
    """
    while True:
        process_audio_samples()  # Process each batch of samples
        time.sleep(WINDOW_STEP / SAMPLE_FREQ)  # Sleep for the time it took to collect the samples

if __name__ == '__main__':
    main()
