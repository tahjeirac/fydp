import copy
import os
import numpy as np
import scipy.fftpack
import sounddevice as sd
import time
import argparse
import json
import wave
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
NoteConversion = {'C4':7, 'B4':1, 'A4':2, 'G4': 3, 'F4':4, 'E4': 5, 'D4':6}

strip = Strip()
songs = Songs("songs.json", MATCH_DELAY, strip)
feedback = []
state_machine = NoteStateMachine(songs, feedback)
start_time = None
played_notes = []


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


def callback_start(indata, frames, time, status):
  """
  Callback function of the InputStream method.
  """
  # define static variables
  if not hasattr(callback_start, "window_samples"):
    callback_start.window_samples = [0 for _ in range(WINDOW_SIZE)]

  if status:
    print(status)
    return
  if any(indata):
    callback_start.window_samples = np.concatenate((callback_start.window_samples, indata[:, 0])) # append new samples
    callback_start.window_samples = callback_start.window_samples[len(indata[:, 0]):] # remove old samples

    signal_power = (np.linalg.norm(callback_start.window_samples, ord=2)**2) / len(callback_start.window_samples)
    signal_power = signal_power * 1000
    volume_db = 10 * np.log10(signal_power) if signal_power > 0 else -np.inf  # dB scale

    global sig
    global vol
    sig.append(signal_power)
    vol.append(volume_db)

   

HANN_WINDOW = np.hanning(WINDOW_SIZE)
def callback(indata, frames, time, status, mean_vol, mean_sig):
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
    # volume_db = 10 * np.log10(signal_power) if signal_power > 0 else -np.inf  # dB scale

    if signal_power < callback.mean_sig - SIG_TOLERANCE:
      os.system('cls' if os.name=='nt' else 'clear')
      print("TOO LOW, Closest note: ...")
      callback.sig_buffer.append(signal_power)
      callback.mean_sig  = np.mean(callback.sig_buffer)  # Output: 30.0
      print ("Mean", callback.mean_sig )
      print(signal_power)
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
      print(f"Closest note: {closest_note} {max_freq}/{closest_pitch}")
      print(f"Signal: {signal_power} dB")  # Display the volume
      print (callback.mean_sig)
      state_machine.handle_input(closest_note)

    else:
      print(f"Closest note: ...")
      callback.sig_buffer.append(signal_power)
      callback.mean_sig  = np.mean(callback.sig_buffer)  # Output: 30.0
      print(f"Signal: {signal_power} dB")  # Display the volume
      state_machine.handle_input("SILENCE")

  else:
    print('no input')

if __name__ == '__main__':
    # Process arguments
    print ("1 for mary 2 for twinkle")
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    parser.add_argument('-s', '--song', type=int, required=True, help='song name to display')

    args = parser.parse_args()

    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')

    try:
      if args.song == 1:
        global MIDI_NOTES
        song_name = "mary"
        print ("Playing Mary Had a Little Lamb")
      else:
         song_name = "twinkle"
         print ("Playing Twinkle Twinkle Little Star")
      
      songs.setSong(song_name)
      strip.colourWipe()


      print ("recording background")
      start_time = time.time()  # Start timing the note
      dur = 0
      # with sd.InputStream(device=1, channels=1, callback=callback_start, blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
      #     while dur <= 15:
      #       dur = time.time() - start_time
      #       time.sleep(0.5)
      
      # print(np.mean(sig))  # Output: 30.0
      # print(np.mean(vol))  # Output: 30.0
      # time.sleep(2)

      # mean_sig = np.mean(sig)
      # mean_vol = np.mean(vol)
      note = songs.setCurrentNote()
      print(note)
      led = NoteConversion.get(note.get("name"))
      print(led)
      strip.startSeq(led)
      start_time = time.time()
      #devvice num hanges?
      with sd.InputStream(device=1, channels=1, callback=partial(callback, mean_vol=0, mean_sig = 0), blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
          while not songs.FINISHED:
            time.sleep(0.5)

      strip.endSeq()
    except KeyboardInterrupt:
        # print (sig[:50])
        # print (vol[:50])
        print(feedback)
        if args.clear:
            strip.colourWipe()
