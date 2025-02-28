import time
import json

class Songs:
    def __init__(self, MATCH_DELAY, strip):

        #self.file_path = file_path
        self.notes = None
        self.NOTE_INDEX = 0
        self.FINISHED = False
        self.LAST_MATCH_TIME = 0  # Store the time of the last match
        self.MATCH_DELAY = MATCH_DELAY # Delay in seconds between allowed matches (0.5s to prevent rapid repeats)
        # self.NoteConversion = {'C3':7, 'B3':1, 'A3':2, 'G3': 3, 'F3':4, 'E3': 5, 'D3':6}
        self.NoteConversion = {'C4':7, 'B4':1, 'A4':2, 'G4': 3, 'F4':4, 'E4': 5, 'D4':6}
        self.Start = True
        self.CurrentNote = None
        self.WrongNoteName = None
        self.StartTime = None
        self.strip = strip
        self.SILENT = True

    def setSilence(self, val=True):
        print ("SILENCE")
        self.SILENT = val

    def setSong(self, song_data): #song_data: json
        # with open(self.file_path, 'r') as file:
        #     data = json.load(file)
        # print (name)
        # self.notes  = data[name]["tracks"][0]["notes"]
        # Accepts JSON data directly instead of loading from a file 
        print(song_data)
        print(f"Setting song: {song_data['title']}")
        for note in song_data["notes"]:
            if 'duration' in note:
                note['duration'] = note['duration'] / 1000  # Convert ms to seconds

        self.notes = song_data["notes"]  # Store the updated notes
        print (self.notes)

        self.NOTE_INDEX = 0  # Reset the note index
        self.FINISHED = False  # Reset the finished flag
        self.setCurrentNote()  # Set the first note

    def setCurrentNote(self):
        if (self.NOTE_INDEX < len(self.notes)):
            note_info = self.notes[self.NOTE_INDEX]
            note = note_info.get("name")
            self.CurrentNote = note_info
            return note_info
        
        self.FINISHED = True
        print("Lesson complete!")
        return "FINI" 
    
    def setWrongNote(self, played_note):
        #turn off previous note if self.WrongNoteName != None & played_note != self.WrongNoteName 
        if self.WrongNoteName != None & played_note != self.WrongNoteName:
            led = self.NoteConversion.get(self.WrongNoteName)
            self.strip.turnOnLED_SOLO(led, False)

        self.WrongNoteName = played_note

        if self.WrongNoteName != None:
            led = self.NoteConversion.get(self.WrongNoteName)
            self.strip.turnOnLED_SOLO(led, True)
                
    
    def nextNote(self):
        # moves to the next note and updates the LED indicator
        self.NOTE_INDEX += 1
        note = self.setCurrentNote()
        note_name = note["note"]
        print(note_name)
        led = self.NoteConversion.get(note_name)
        print(led)
        if led:
            if note.get("duration") > 480:
                print("h")
                self.strip.turnOnLED(led, "h")
            else:
                print("q")
                self.strip.turnOnLED(led, "q")


    def noteMatch(self, played_note):
        print (self.CurrentNote.get("note"))
        if (time.time()  - self.LAST_MATCH_TIME > self.MATCH_DELAY) and self.SILENT:
                        #enough time has passed
            if played_note == self.CurrentNote.get("note"):
                print("Match!")
                if self.Start:
                    #first match
                    self.StartTime = time.time()
                    self.Start = False
                else:
                    duration = time.time()  - self.StartTime
                    print (duration)
                    print(self.CurrentNote.get("duration"))
                    if duration >= 2*self.CurrentNote.get("duration"):
                        #played long enough
                        print("DONE")
                        self.Start = True
                        self.NOTE_INDEX = self.NOTE_INDEX+1 # get nxt not
                        self.LAST_MATCH_TIME = time.time() 
                        self.setSilence(False)

                        if (self.NOTE_INDEX < len(self.notes)):
                            note_info = self.notes[self.NOTE_INDEX]
                            note = note_info.get("note")
                            self.CurrentNote = note_info
                            led = self.NoteConversion.get(note)
                            print(led)
                            if led:
                                if self.CurrentNote.get("duration") > 480:
                                    print("h")
                                    self.strip.turnOnLED(led, "h")
                                else:
                                    print("q")
                                    self.strip.turnOnLED(led, "q")
                        else:
                            self.FINISHED = True
            
            else:
                print ("no match")
                self.Start = True


