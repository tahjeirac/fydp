import time
import json

class Songs:
    def __init__(self, file_path, MATCH_DELAY):

        self.file_path = file_path
        self.notes = None
        self.NOTE_INDEX = 0
        self.FINISHED = False
        self.LAST_MATCH_TIME = 0  # Store the time of the last match
        self.MATCH_DELAY = MATCH_DELAY # Delay in seconds between allowed matches (0.5s to prevent rapid repeats)
        self.NoteConversion = {'C3':7, 'B3':1, 'A3':2, 'G3': 3, 'F3':4, 'E3': 5, 'D3':6}
        self.Start = True
        self.CurrentNote = None
        self.StartTime = None

    def setSong(self, name):
        with open(self.file_path, 'r') as file:
            data = json.load(file)
        print (name)
        self.notes  = data[name]["tracks"][0]["notes"]

    def getCurrentNote(self):
        if (self.NOTE_INDEX < len(self.notes)):
            note_info = self.notes[self.NOTE_INDEX]
            note = note_info.get("name")
            self.CurrentNote = note_info
            return note
        self.FINISHED = True
        return "FINI" 
        
    def noteMatch(self, played_note):
        print (self.CurrentNote.get("name"))
        if time.time()  - self.LAST_MATCH_TIME > self.MATCH_DELAY:
                        #enough time has passed
            if played_note == self.CurrentNote.get("name"):
                print("Match!")
                if self.Start:
                    #first match
                    self.StartTime = time.time()
                    self.Start = False
                else:
                    duration = time.time()  - self.StartTime
                    print (duration)
                    print(self.CurrentNote.get("duration"))
                    if duration >= self.CurrentNote.get("duration"):
                        #played long enough
                        print("DONE")
                        self.Start = True
                        self.NOTE_INDEX = self.NOTE_INDEX+1
                        self.LAST_MATCH_TIME = time.time() 

                if (self.NOTE_INDEX < len(self.notes)):
                    note_info = self.notes[self.NOTE_INDEX]
                    note = note_info.get("name")
                    self.CurrentNote = note_info
                    led = self.NoteConversion.get(note)
                    print(led)
                    if led:
                        return led
                    
                else:
                    self.FINISHED = True
                    return -1
            
            else:
                print ("no match")
                self.Start = True
                led = self.NoteConversion.get(self.CurrentNote.get("name"))
                if led:
                    return led

