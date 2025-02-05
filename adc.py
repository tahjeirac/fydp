import copy
import os
import numpy as np
import scipy.fftpack
import spidev
import time
import RPi.GPIO as GPIO

from led_control import Strip
from songs import Songs
from state import NoteStateMachine

# ADC Configuration
GPIO.setmode(GPIO.BCM)
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

CS_ADC = 12
GPIO.setup(CS_ADC, GPIO.OUT)

def ReadChannel3208(channel):
    adc = spi.xfer2([6 | (channel >> 2), channel << 6, 0])
    data = ((adc[1] & 15) << 8) + adc[2]
    return data

def ConvertToVoltage(value, bitdepth, vref):
    return vref * (value / (2**bitdepth - 1))

# General settings
SAMPLE_FREQ = 48000
WINDOW_SIZE = 48000
WINDOW_STEP = 12000
NUM_HPS = 5
POWER_THRESH = 1e-6
CONCERT_PITCH = 440
WHITE_NOISE_THRESH = 0.2

DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]
MATCH_DELAY = 0.7
ALL_NOTES = ["A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"]

NoteConversion = {'C4': 7, 'B4': 1, 'A4': 2, 'G4': 3, 'F4': 4, 'E4': 5, 'D4': 6}

strip = Strip()
songs = Songs("songs.json", MATCH_DELAY, strip)
state_machine = NoteStateMachine(songs)

HANN_WINDOW = np.hanning(WINDOW_SIZE)

def find_closest_note(pitch):
    i = int(np.round(np.log2(pitch / CONCERT_PITCH) * 12))
    closest_note = ALL_NOTES[i % 12] + str(4 + (i + 9) // 12)
    closest_pitch = CONCERT_PITCH * 2**(i / 12)
    return closest_note, closest_pitch

def process_audio():
    window_samples = np.zeros(WINDOW_SIZE)
    note_buffer = ["1", "2"]
    
    while not songs.FINISHED:
        for i in range(WINDOW_SIZE):
            GPIO.output(CS_ADC, GPIO.LOW)
            value = ReadChannel3208(1)  # Read ADC channel 1
            GPIO.output(CS_ADC, GPIO.HIGH)
            window_samples[i] = ConvertToVoltage(value, 12, 3.3)  # Convert ADC value to voltage
            time.sleep(1 / SAMPLE_FREQ)
        
        # Signal Power Check
        signal_power = np.linalg.norm(window_samples, ord=2)**2 / len(window_samples)
        if signal_power < POWER_THRESH:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Closest note: ...")
            continue
        
        # Apply Hanning window & FFT
        hann_samples = window_samples * HANN_WINDOW
        magnitude_spec = abs(scipy.fftpack.fft(hann_samples)[: len(hann_samples) // 2])
        
        # Suppress noise
        for i in range(int(62 / DELTA_FREQ)):
            magnitude_spec[i] = 0
        
        # Suppress white noise in octave bands
        for j in range(len(OCTAVE_BANDS) - 1):
            ind_start = int(OCTAVE_BANDS[j] / DELTA_FREQ)
            ind_end = min(int(OCTAVE_BANDS[j + 1] / DELTA_FREQ), len(magnitude_spec))
            avg_energy = np.linalg.norm(magnitude_spec[ind_start:ind_end], ord=2) / (ind_end - ind_start)
            for i in range(ind_start, ind_end):
                magnitude_spec[i] = magnitude_spec[i] if magnitude_spec[i] > WHITE_NOISE_THRESH * avg_energy else 0
        
        # Harmonic Product Spectrum (HPS)
        mag_spec_ipol = np.interp(np.arange(0, len(magnitude_spec), 1 / NUM_HPS), np.arange(0, len(magnitude_spec)), magnitude_spec)
        mag_spec_ipol /= np.linalg.norm(mag_spec_ipol, ord=2)
        hps_spec = copy.deepcopy(mag_spec_ipol)
        
        for i in range(NUM_HPS):
            tmp_hps_spec = np.multiply(hps_spec[: int(np.ceil(len(mag_spec_ipol) / (i + 1)))], mag_spec_ipol[:: (i + 1)])
            if not any(tmp_hps_spec):
                break
            hps_spec = tmp_hps_spec
        
        max_ind = np.argmax(hps_spec)
        max_freq = max_ind * (SAMPLE_FREQ / WINDOW_SIZE) / NUM_HPS
        print (max_freq)
        closest_note, closest_pitch = find_closest_note(max_freq)
        
        note_buffer.insert(0, closest_note)
        note_buffer.pop()
        
        os.system('cls' if os.name == 'nt' else 'clear')
        if note_buffer.count(note_buffer[0]) == len(note_buffer):
            print(f"Closest note: {closest_note} {max_freq:.1f}/{closest_pitch:.1f}")
            state_machine.handle_input(closest_note)
        else:
            print("Closest note: ...")
            state_machine.handle_input("SILENCE")
        
        time.sleep(0.5)  # Match delay

if __name__ == '__main__':
    print("1 for Mary, 2 for Twinkle")
    song_choice = int(input("Enter song choice: "))
    song_name = "mary" if song_choice == 1 else "twinkle"
    print(f"Playing {song_name.replace('_', ' ').title()}")
    
    songs.setSong(song_name)
    # strip.colourWipe()
    note = songs.setCurrentNote()
    led = NoteConversion.get(note.get("name"))
    # strip.startSeq(led)
    
    try:
        process_audio()
        # strip.endSeq()
    except KeyboardInterrupt:
        # strip.colourWipe()
        GPIO.cleanup()
