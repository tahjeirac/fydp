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
    
    def setSong(self, name):
        with open(self.file_path, 'r') as file:
            data = json.load(file)
        print (name)
        self.notes  = data[name]["tracks"][0]["notes"]

    def getCurrentNote(self):
        if (self.NOTE_INDEX < len(self.notes)):
            print("hi")
            note_info = self.notes[self.NOTE_INDEX]
            print(note_info)
            note = note_info.get("name")
            print(note)
            return note
        self.FINISHED = True
        return "FINI" 
        
    def noteMatch(self):
        print("Match")
        current_time = time.time()  # Get the current time
        if current_time - self.LAST_MATCH_TIME > self.MATCH_DELAY:

            self.NOTE_INDEX = self.NOTE_INDEX+1
            if (self.NOTE_INDEX < len(self.notes)):
                note_info = self.notes[self.NOTE_INDEX]
                note = note_info.get("name")
                led = self.NoteConversion.get(note)
                self.LAST_MATCH_TIME = current_time 
                if led:
                    return led
                
            else:
                self.FINISHED = True
                return -1
          
   

