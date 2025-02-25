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

from led_control import Strip
from songs import Songs
from state import NoteStateMachine
# General settings that can be changed by the user
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


MATCH_DELAY = 0.7 # Delay in seconds between allowed matches (0.5s to prevent rapid repeats)
ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]

# NoteConversion = {'C3':7, 'B3':1, 'A3':2, 'G3': 3, 'F3':4, 'E3': 5, 'D3':6}
NoteConversion = {'C4':7, 'B4':1, 'A4':2, 'G4': 3, 'F4':4, 'E4': 5, 'D4':6}

strip = Strip()
songs = Songs("songs.json", MATCH_DELAY, strip)
state_machine = NoteStateMachine(songs)
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


HANN_WINDOW = np.hanning(WINDOW_SIZE)
fig, (ax_time, ax_freq) = plt.subplots(2, 1, figsize=(10, 6))  # Create two subplots


def setup_plots():
    # Time-domain plot
    ax_time.set_title('Time Domain Signal')
    ax_time.set_xlabel('Time (s)')
    ax_time.set_ylabel('Amplitude')
    ax_time.set_xlim(0, WINDOW_T_LEN)  # Adjust time axis range
    ax_time.set_ylim(-1, 1)  # Amplitude range
    
    # Frequency-domain plot (DFT)
    ax_freq.set_title('Magnitude Spectrum (DFT)')
    ax_freq.set_xlabel('Frequency (Hz)')
    ax_freq.set_ylabel('Magnitude')
    ax_freq.set_xlim(0, SAMPLE_FREQ / 2)  # Limit x-axis to Nyquist frequency
    ax_freq.set_ylim(0, 1)  # Magnitude range (normalized)

    plt.tight_layout()  # Adjust subplots for clarity
    plt.ion()  # Turn interactive mode on to update the plots dynamically
    plt.show()

def update_plots(time_data, freq_data):
    # Time-domain plot update
    ax_time.clear()
    ax_time.plot(np.linspace(0, len(time_data) * SAMPLE_T_LENGTH, len(time_data)), time_data)
    
    # Frequency-domain plot update (using magnitude of FFT)
    ax_freq.clear()
    ax_freq.plot(np.linspace(0, SAMPLE_FREQ / 2, len(freq_data)), freq_data)

    plt.draw()  # Redraw the plots to update them
    plt.pause(0.001)  # Pause briefly to allow for UI updates

def callback(indata, frames, time, status):
    """
    Callback function for real-time audio processing.
    """
    global callback  # Make sure we're referring to the correct global callback function

    if status:
        print('Status:', status)
        return
    
    if any(indata):  # Only process if there's audio data
        # Prepare the time-domain signal
        callback.window_samples = np.concatenate((callback.window_samples, indata[:, 0]))  # Append new samples
        callback.window_samples = callback.window_samples[len(indata[:, 0]):]  # Remove old samples

        # Signal power check
        signal_power = np.linalg.norm(callback.window_samples, ord=2) ** 2 / len(callback.window_samples)
        if signal_power < POWER_THRESH:
            return

        # Apply Hanning window to avoid spectral leakage
        hann_samples = callback.window_samples * HANN_WINDOW

        # Compute DFT (FFT)
        magnitude_spec = abs(scipy.fftpack.fft(hann_samples)[:len(hann_samples) // 2])

        # Update plots: time-domain and frequency-domain (DFT)
        update_plots(callback.window_samples, magnitude_spec)

        # Note detection (as per your original code)
        max_ind = np.argmax(magnitude_spec)
        max_freq = max_ind * (SAMPLE_FREQ / WINDOW_SIZE)

        closest_note, closest_pitch = find_closest_note(max_freq)
        print(f"Closest note: {closest_note} at {max_freq:.2f} Hz")

        # Optional: You can continue with your state machine logic or additional processing here
        callback.noteBuffer.insert(0, closest_note)
        callback.noteBuffer.pop()
def saveNote(note):
   #save time
   # note
   time_played = time.time()   # Start timing the note
   note_info = {"time_played":time_played, "note":  note}
   played_notes.append(note_info)
   return

# def makeFeedback ():
#    # Example input: list of dictionaries with time_played and note
# # Convert to note-duration format
#   note_durations = []

#   for i in range(1, len(played_notes)):  # Start from second element
#     prev = note_data[i - 1]
#     curr = note_data[i]
#     duration = curr["time_played"] - prev["time_played"]

#     note_durations.append({"note": prev["note"], "duration": duration})

#     # Add last note with unknown duration (optional: set to None or estimate)
#     note_durations.append({"note": note_data[-1]["note"], "duration": None})

#     # Output result
#   print(note_durations)

  # return
   #block periods of same notes togeter and such
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

      note = songs.setCurrentNote()
      print(note)
      led = NoteConversion.get(note.get("name"))
      print(led)
      strip.startSeq(led)
      start_time = time.time()
      #devvice num hanges?
      with sd.InputStream(device=1, channels=1, callback=callback, blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
          while not songs.FINISHED:
            time.sleep(0.5)

      strip.endSeq()
    except KeyboardInterrupt:
        if args.clear:
            strip.colourWipe()
