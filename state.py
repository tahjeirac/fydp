import time
import json


class NoteStateMachine:
    def __init__(self, song, feedback):
        self.song = song
        self.state = "starting"  # Initial state
        self.current_duration = 0  # Tracks how long a note has been sustained
        self.start_time = None
        self.last_match_time = None
        self.feedback = feedback
        self.duaration_met = False
        self.minimum_silence = 0.5


    def transition(self, new_state):
        print(f"Transitioning from {self.state} to {new_state}")
        self.state = new_state

    
    def starting(self, played_note):
        self.start_time = time.perf_counter()
  # Start timing the note
        if played_note == "SILENCE":
            print(" WAITING FOR  OF SILENCE...")
            self.transition("silent_start")
    
    def silent_start(self, played_note):
        if played_note == "SILENCE":
            silence_duration = time.perf_counter() - self.start_time
            print("WAITING FOR 10S OF SILENCE...", silence_duration)
            if silence_duration > self.minimum_silence:
                print(" Good to start", silence_duration)
                self.song.start()
                self.transition("waiting")
        else:
            self.transition("starting")


    def waiting(self, played_note):
        current_note_name = self.song.CurrentNote.get("note")
        print(f"Waiting for: {current_note_name}, Received: {played_note}")

        if played_note == current_note_name:
            self.start_time = time.perf_counter()
  # Start timing the note
            self.transition("listening")

        elif played_note == "SILENCE":
            print("Still waiting...")
        else:
            print("Wrong note!")
            self.start_time = time.perf_counter()
  # Start timing the note
            self.transition("listening_wrong_note")

    def listening(self, played_note):
        current_note_name = self.song.CurrentNote.get("note")
        intended_duration = self.song.CurrentNote.get("duration")

        if played_note == current_note_name:
            self.current_duration = time.perf_counter() - self.start_time
            print(f"Listening: {played_note} for {self.current_duration:.2f}s out of {intended_duration:.2f}s")

        elif played_note == "SILENCE": #not relased
            #check if long enoguh
            if self.current_duration <= intended_duration: #played too short
                print("Silence detected! and note not held for right time")
                self.record_feedback(current_note_name)
                self.transition("waiting")
            # elif self.current_duration <= 3 * intended_duration: #played long enogu change times
            else:
                print("Silence detected! and note held for right time")
                self.record_feedback(current_note_name)
                self.song.nextNote() #set to next note
                self.transition("waiting") 
            # else: #turn red maybe? flash? played too long
            #     #flash
            #     self.record_feedback(current_note_name)
            #     print("Silence detected! and note held for too long")
            #     self.transition("waiting") 
        else:
            print("Wrong note detected!")
            self.song.setWrongNote(played_note)
            self.record_feedback(current_note_name)
            self.start_time = time.perf_counter()
  # Start timing the note
            self.transition("listening_wrong_note")

    def listening_wrong_note(self, played_note): #FIX THIS
        current_note_name = self.song.CurrentNote.get("note")
        current_wrong_note_name = self.song.WrongNoteName
        print(f"Waiting for: {current_note_name}, Currently Playing: {played_note}")
        self.current_duration = time.perf_counter() - self.start_time

        if played_note == current_wrong_note_name:
            print("Wrong note being held")
            self.current_duration = time.perf_counter() - self.start_time
        elif played_note == current_note_name:
            self.song.setWrongNote(None)
            self.record_feedback(current_wrong_note_name)
            self.start_time = time.perf_counter()
  # Start timing the note
            self.transition("listening")
        elif played_note == "SILENCE":
            self.song.setWrongNote(None)
            self.record_feedback(current_wrong_note_name)
            print("Silence detected!")
            self.transition("waiting")
        else: #new wrong note
            self.record_feedback(current_wrong_note_name)
            self.start_time = time.perf_counter()
  # Start timing the note
            self.song.setWrongNote(played_note)
        
    def record_feedback(self, played_note):
        print ("recording feedback", played_note)
        if played_note:
            self.feedback.append({played_note:self.current_duration})

    def idle(self, played_note):
        if played_note == "SILENCE":
            self.song.nextNote()
            self.transition("waiting")

    def handle_input(self, played_note):
        if self.state == "starting":
            self.starting(played_note)
        elif self.state == "silent_start":
            self.silent_start(played_note)
        elif self.state == "waiting":
            self.waiting(played_note)
        elif self.state == "listening":
            self.listening(played_note)
        elif self.state == "idle":
            self.idle(played_note)
        elif self.state == "listening_wrong_note":
            self.listening_wrong_note(played_note)