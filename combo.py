import copy
import os
import numpy as np
import scipy.fftpack
import sounddevice as sd
import time
import argparse
import json
import wave
import requests
import subprocess
import matplotlib.pyplot as plt
from functools import partial
from collections import deque

from led_control import Strip
from songs import Songs
from state import NoteStateMachine

SAMPLE_FREQ = 48000 # sample frequency in Hz
WINDOW_SIZE = 48000 # window size of the DFT in samples
WINDOW_STEP = 12000 # step size of window
NUM_HPS = 5 # max number of harmonic product spectrums
POWER_THRESH = 1e-6 # tuning is activated if the signal power exceeds this threshold
CONCERT_PITCH = 440 # defining a1
WHITE_NOISE_THRESH = 0.2 # everything under WHITE_NOISE_THRESH*avg_energy_per_freq is cut off

WINDOW_T_LEN = WINDOW_SIZE / SAMPLE_FREQ # length of the window in seconds
SAMPLE_T_LENGTH = 1 / SAMPLE_FREQ # length between two samples in seconds
DELTA_FREQ = SAMPLE_FREQ / WINDOW_SIZE # frequency step width of the interpolated DFT
OCTAVE_BANDS = [50, 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600]

SIG_TOLERANCE = 0.0005

MATCH_DELAY = 0.7 # Delay in seconds between allowed matches (0.5s to prevent rapid repeats)
ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]

# NoteConversion = {'C3':7, 'B3':1, 'A3':2, 'G3': 3, 'F3':4, 'E3': 5, 'D3':6}
# NoteConversion = {'C4':7, 'B4':1, 'A4':2, 'G4': 3, 'F4':4, 'E4': 5, 'D4':6}
NoteConversion = {'C6':2, 'B6':3, 'A6':4, 'G5':5, 'F5':6, 'E5':7, 'D5':8, 'C5':9, 'B5': 10, 'A5':11, 'G4':12, 'F4':13, 'E4':14, 'D4':15, 'C4':16, 'B4': 17, 'A4': 18, 'G3':19, 'F3':20, 'E3':21, 'D3':22, 'C3':23}
# NoteConversion = {'C6':3}
strip = Strip()
songs = Songs(MATCH_DELAY, strip, note_conversion=NoteConversion)
feedback = []
state_machine = NoteStateMachine(songs, feedback)
start_time = None
played_notes = []

SERVER_URL = "http://192.168.4.1:5000"
file_path = "song.json"
file_path_no_app = "song_no_app.json"

def clear_file(file_path):
    # Open the file in write mode, which clears the contents
    with open(file_path, 'w'):
        pass  # No need to write anything, just open and close the file
    
def fetch_song():
    # fetching the song data from the server 
    data_recv = False
    song_data = None
    while not data_recv:
      try:
          # response = requests.post(f"{SERVER_URL}/receive_json")
          
          with open(file_path_no_app, 'r') as file:
            content = file.read().strip()  # Read content and remove any extra whitespace
            if content:
                data_recv = True
                song_data = json.loads(content)
                songs.setSong(song_data)
                print("File has data:", content)
            else:
                print("File is empty")
          time.sleep(1)

      except Exception as e:
          print(f"Error fetching song: {e}")
    
    clear_file(file_path)


def find_closest_note(pitch):
  """
  This function finds the closest note for a given pitch
  Parameters:
    pitch (float): pitch given in hertz
  Returns:
    closest_note (str): e.g. a, g#, ..
    closest_pitch (float): pitch of the closest note in hertz
  """
  i = int(np.round(np.log2(pitch/CONCERT_PITCH)*12))
  closest_note = ALL_NOTES[i%12] + str(4 + (i + 9) // 12)
  closest_pitch = CONCERT_PITCH*2**(i/12)
  return closest_note, closest_pitch

sig = deque(maxlen= 10)
vol = []


HANN_WINDOW = np.hanning(WINDOW_SIZE)
MINIMUM_SILENCE_DURATION = 5

def get_rpi_device():
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if "snd_rpi" in device["name"].lower() and device["max_input_channels"] > 0:
            return i  # Return the index of the Raspberry Pi audio input device
    return None  # Return None if not found

def callback(indata, frames, time, status):
  """
  Callback function of the InputStream method.
  """
  # define static variables
  if not hasattr(callback, "window_samples"):
    callback.window_samples = [0 for _ in range(WINDOW_SIZE)]
  if not hasattr(callback, "noteBuffer"):
    callback.noteBuffer = ["1","2"]
  if not hasattr(callback, "mean_sig"):
    callback.mean_sig = 0
  if not hasattr(callback, "sig_buffer"):
    callback.sig_buffer = deque(maxlen= 10)

  if status:
    print(status)
    return
  if any(indata):
    callback.window_samples = np.concatenate((callback.window_samples, indata[:, 0])) # append new samples
    callback.window_samples = callback.window_samples[len(indata[:, 0]):] # remove old samples

    # skip if signal power is too low
    signal_power = (np.linalg.norm(callback.window_samples, ord=2)**2) / len(callback.window_samples)
    signal_power = signal_power * 1000

    if signal_power < callback.mean_sig - SIG_TOLERANCE:
      os.system('cls' if os.name=='nt' else 'clear')
      callback.sig_buffer.append(signal_power)
      callback.mean_sig  = np.mean(callback.sig_buffer)  # Output: 30.0
      state_machine.handle_input("SILENCE")

      # print ("Mean", callback.mean_sig )
      # print(signal_power)
      return

    # avoid spectral leakage by multiplying the signal with a hann window
    hann_samples = callback.window_samples * HANN_WINDOW
    magnitude_spec = abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples)//2])

    # supress mains hum, set everything below 62Hz to zero
    for i in range(int(62/DELTA_FREQ)):
      magnitude_spec[i] = 0


    # calculate average energy per frequency for the octave bands
    # and suppress everything below it
    for j in range(len(OCTAVE_BANDS)-1):
      ind_start = int(OCTAVE_BANDS[j]/DELTA_FREQ)
      ind_end = int(OCTAVE_BANDS[j+1]/DELTA_FREQ)
      ind_end = ind_end if len(magnitude_spec) > ind_end else len(magnitude_spec)
      avg_energy_per_freq = (np.linalg.norm(magnitude_spec[ind_start:ind_end], ord=2)**2) / (ind_end-ind_start)
      avg_energy_per_freq = avg_energy_per_freq**0.5
      for i in range(ind_start, ind_end):
        magnitude_spec[i] = magnitude_spec[i] if magnitude_spec[i] > WHITE_NOISE_THRESH*avg_energy_per_freq else 0

    # interpolate spectrum
    mag_spec_ipol = np.interp(np.arange(0, len(magnitude_spec), 1/NUM_HPS), np.arange(0, len(magnitude_spec)),
                              magnitude_spec)
    mag_spec_ipol = mag_spec_ipol / np.linalg.norm(mag_spec_ipol, ord=2) #normalize it

    hps_spec = copy.deepcopy(mag_spec_ipol)

    # calculate the HPS
    for i in range(NUM_HPS):
      tmp_hps_spec = np.multiply(hps_spec[:int(np.ceil(len(mag_spec_ipol)/(i+1)))], mag_spec_ipol[::(i+1)])
      if not any(tmp_hps_spec):
        break
      hps_spec = tmp_hps_spec

    max_ind = np.argmax(hps_spec)
    max_freq = max_ind * (SAMPLE_FREQ/WINDOW_SIZE) / NUM_HPS
    closest_note, closest_pitch = find_closest_note(max_freq)
    max_freq = round(max_freq, 1)
    closest_pitch = round(closest_pitch, 1)

    callback.noteBuffer.insert(0, closest_note) # ringbuffer
    callback.noteBuffer.pop()

    os.system('cls' if os.name=='nt' else 'clear')
    if callback.noteBuffer.count(callback.noteBuffer[0]) == len(callback.noteBuffer):
      state_machine.handle_input(closest_note)


    else:
      print(f"Closest note: ...")
      callback.sig_buffer.append(signal_power)
      callback.mean_sig  = np.mean(callback.sig_buffer)  # Output: 30.0
      state_machine.handle_input("SILENCE")

  else:
    print('no input')

if __name__ == '__main__':
    # Process arguments

      strip.colourWipe()
      clear_file(file_path)
      clear_file("feedback.json")

      print ('Press Ctrl-C to quit.')
      # server_process = subprocess.Popen(["python3", "wifi-server.py"])
      print ("WIFI STARTED")
      try:
        while True:
          strip.turnOnLED_SOLO(0, True)
          time.sleep(2)

          strip.turnOnLED_SOLO(1, True)
          time.sleep(2)

          strip.turnOnLED_SOLO(2,True)
          time.sleep(2)

          strip.turnOnLED_SOLO(3, True)
          time.sleep(2)

          strip.turnOnLED_SOLO(4, True)
          time.sleep(2)
          strip.turnOnLED_SOLO(5,True)
          time.sleep(10)
          # fetch_song()
          # strip.colourWipe()

          # rpi_device = get_rpi_device()
          # print(f"Raspberry Pi audio device number: {rpi_device}")
          # with sd.InputStream(device=rpi_device, channels=1, callback=callback, blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
          #     while not songs.FINISHED:
          #       time.sleep(0.25)

          # strip.endSeq()
          # print(feedback)
          # headers = {"Content-Type": "application/json"}
          # response = requests.post(f"{SERVER_URL}/send_feedback", data=json.dumps(feedback), headers=headers)
          # print(f"Server Response: {response.status_code}, {response.text}")

      except KeyboardInterrupt:
          strip.colourWipe()

          print(feedback)

