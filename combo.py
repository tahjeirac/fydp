import copy
import os
import numpy as np
import scipy.fftpack
import sounddevice as sd
import time
import argparse
import json

from led_control import Strip


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

ALL_NOTES = ["A","A#","B","C","C#","D","D#","E","F","F#","G","G#"]

NoteConversion = {'C4':7, 'B4':1, 'A4':2, 'G4': 3, 'F4':4, 'E4': 5, 'D4':6}

NOTES = ['E4', 'D4', 'C4', 'D4', 'E4', 'E4', 'E4', 'D4', 'D4', 'D4', 'E4', 'G4', 'G4', 'E4', 'D4', 'C4', 'D4', 'E4', 'E4', 'E4', 'E4', 'D4', 'D4', 'E4', 'D4', 'E4', 'C4']

strip = Strip()

file_path = "mary.json"  # Replace with the actual file path

# Open the JSON file and load the data
with open(file_path, 'r') as file:
    data = json.load(file)

MIDI_NOTES = data["tracks"][0]["notes"]


NOTE_INDEX = 0
FINISHED = False
LAST_MATCH_TIME = 0  # Store the time of the last match
MATCH_DELAY = 0.8 # Delay in seconds between allowed matches (0.5s to prevent rapid repeats)
 
   

def noteMatch():
    print("Match")
    global NOTE_INDEX
    global NoteConversion
    global FINISHED
    global LAST_MATCH_TIME  # To track the last time a note was matched
    current_time = time.time()  # Get the current time
    if current_time - LAST_MATCH_TIME > MATCH_DELAY:

        NOTE_INDEX = NOTE_INDEX+1
        if (NOTE_INDEX < len(MIDI_NOTES                                                                                                                                                                              )):
            note_info = MIDI_NOTES[NOTE_INDEX]
            note = note_info.get("name")
            led = NoteConversion.get(note)
            LAST_MATCH_TIME = current_time 
            if led:
                print(f"displaying Note:{note} on LED number:{led}")
                strip.turnOnLED(led)
        else:
            FINISHED = True
          
   
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

def getCurrentNote():
    global FINISHED
    if (NOTE_INDEX < len(NOTES)):
      return NOTES[NOTE_INDEX]
    FINISHED = True
    return "FINI"

HANN_WINDOW = np.hanning(WINDOW_SIZE)
def callback(indata, frames, time, status):
  """
  Callback function of the InputStream method.
  That's where the magic happens ;)
  """
  global FINISHED

  currentNote = getCurrentNote()
  
  # define static variables
  if not hasattr(callback, "window_samples"):
    callback.window_samples = [0 for _ in range(WINDOW_SIZE)]
  if not hasattr(callback, "noteBuffer"):
    callback.noteBuffer = ["1","2"]

  if status:
    print('s')
    print(status)
    return
  if any(indata):
    callback.window_samples = np.concatenate((callback.window_samples, indata[:, 0])) # append new samples
    callback.window_samples = callback.window_samples[len(indata[:, 0]):] # remove old samples

    # skip if signal power is too low
    signal_power = (np.linalg.norm(callback.window_samples, ord=2)**2) / len(callback.window_samples)
    volume_db = 10 * np.log10(signal_power) if signal_power > 0 else -np.inf  # dB scale

    print(f"Volume: {volume_db:.2f} dB")  # Display the volume
    print(signal_power)
    if signal_power < POWER_THRESH:
      os.system('cls' if os.name=='nt' else 'clear')
      print("Closest note: ...")
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

    callback.noteBuffer.insert(0, closest_note) # note that this is a ringbuffer
    callback.noteBuffer.pop()

    os.system('cls' if os.name=='nt' else 'clear')
    if callback.noteBuffer.count(callback.noteBuffer[0]) == len(callback.noteBuffer):
      print(f"Closest note: {closest_note} {max_freq}/{closest_pitch}")
      print(currentNote)
      global NOTE_INDEX
      print(NOTE_INDEX)
      if currentNote == closest_note:
          noteMatch()

    else:
      print(f"Closest note: ...")

  else:
    print('no input')

if __name__ == '__main__':
    # Process arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clear', action='store_true', help='clear the display on exit')
    args = parser.parse_args()


    print ('Press Ctrl-C to quit.')
    if not args.clear:
        print('Use "-c" argument to clear LEDs on exit')

    try:
      strip.colourWipe()
      note_info = MIDI_NOTES[NOTE_INDEX]
      note = note_info.get("name")
      led = NoteConversion.get(note)
      strip.startSeq(led)
      print ("Starting Song!")
      with sd.InputStream(device=1, channels=1, callback=callback, blocksize=WINDOW_STEP, samplerate=SAMPLE_FREQ):
          while not FINISHED:
            time.sleep(0.5)

      strip.endSeq()
    except KeyboardInterrupt:
        if args.clear:
            strip.colourWipe()
