import time
import json


class NoteStateMachine:
    def __init__(self, song):
        self.song = song
        self.state = "waiting"  # Initial state
        self.current_duration = 0  # Tracks how long a note has been sustained
        self.start_time = None
        self.last_match_time = None


    def transition(self, new_state):
        print(f"Transitioning from {self.state} to {new_state}")
        self.state = new_state

    
    def waiting(self, played_note):
        current_note_name = self.song.getCurrentNote()["name"]
        print(f"Waiting for: {current_note_name}, Received: {played_note}")

        if played_note == current_note_name:
            self.start_time = time.time()  # Start timing the note
            self.transition("listening")

        elif played_note == "SILENCE":
            print("Still waiting...")
        else:
            print("Wrong note!")

    def listening(self, played_note):
        current_note_name = self.song.getCurrentNote()["name"]
        intended_duration = self.song.CurrentNote.get("duration")

        if played_note == current_note_name:
            self.current_duration = time.time() - self.start_time
            print(f"Listening: {played_note} for {self.current_duration:.2f}s")

            if self.current_duration >= 2 * intended_duration: #played long enough
                print("Changing to the next note...")
                self.song.nextNote()

                self.transition("idle")
        else:
            print("Wrong note or silence detected!")
            self.transition("waiting")

    
    def idle(self, played_note):
        if played_note == "SILENCE":
            self.transition("waiting")

    def handle_input(self, played_note):
        if self.state == "waiting":
            self.waiting(played_note)
        elif self.state == "listening":
            self.listening(played_note)
        elif self.state == "idle":
            self.idle(played_note)

