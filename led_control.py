import time
from rpi_ws281x import *


# LED strip configuration:


CLEAR = Color(0,0,0)
RED = Color(255,0,0)
ROSE = Color(255,0,128)

MAGENTA = Color(255,0,255)
VIOLET = Color(128,0,255)

BLUE = Color(255,255,0)
CYAN = Color(0,255,255)

GREEN = Color(0,255,0)

CHART = Color(128,255,0)
YELLOW = Color(255,255,0)

WHITE = Color(255,255,255)
ORANGE = Color(255,165,0)

class Strip:
    def __init__(self):
        self.LED_COUNT      = 24     # Number of LED pixels.
        self.LED_PIN        = 13      # GPIO pin connected to the pixels (18 uses PWM!).
        self.LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
        self.LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
        self.LED_BRIGHTNESS = 65     # Set to 0 for darkest and 255 for brightest
        self.LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
        self.LED_CHANNEL    = 1       # set to '1' for GPIOs 13, 19, 41, 45 or 53
        self.LAST = Color(0, 255, 0)
        self.LED_ON = -1
        self.QUARTER = [YELLOW, GREEN]
        self.HALF = [BLUE, CYAN]
        self.WHOLE = [VIOLET, MAGENTA]
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.strip.begin()


    def blinkLED(self, led):
        self.strip.setPixelColor(led, BLUE)
        self.strip.show()
        time.sleep(0.5)
        self.strip.setPixelColor(led, CLEAR)
        self.strip.show()
        time.sleep(0.5)

    def turnOnLED(self, led, note_type="q"):
        c = Color(0, 255, 0)
        if self.LED_ON != -1:
            #turn off last led
            self.strip.setPixelColor(self.LED_ON, Color(0,0,0))
            self.strip.show()

        if self.LED_ON == led:
            #same note as last time
            self.COLOUR_INDEX =  0 if self.COLOUR_INDEX == 1 else 1
            if note_type == "q":
                c = self.QUARTER[self.COLOUR_INDEX]
            elif note_type == "h":
                c = self.HALF[self.COLOUR_INDEX]
            elif note_type == "w":
                c = self.WHOLE[self.COLOUR_INDEX]
            else:
                c =  Color(0, 255, 0)
        else:
            self.COLOUR_INDEX = 0
            if note_type == "q":
                c = self.QUARTER[self.COLOUR_INDEX]
            elif note_type == "h":
                c = self.HALF[self.COLOUR_INDEX]
            elif note_type == "w":
                c = self.WHOLE[self.COLOUR_INDEX]
            else:
                c =  Color(0, 255, 0)

        self.strip.setPixelColor(led, c)
        self.strip.show()
        self.LED_ON = led

    def turnOnLED_SOLO(self, led, set):
        #TO DO
        if led:
            if set == True:
                self.strip.setPixelColor(led, RED)
            else:
                self.strip.setPixelColor(led, CLEAR)
            self.strip.show()
        print("turn red")

    def show_ON(self):
        self.strip.setPixelColor(23, GREEN)
        self.strip.show()

    def showIndicator(self, led):
        self.strip.setPixelColor(led, ORANGE)
        self.strip.show() 
    
    def turn_OFF(self, led):
        self.strip.setPixelColor(led, CLEAR)
        self.strip.show()

    def wheel(self, pos):
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    def rainbow(self, wait_ms=20, iterations=1):
        """Draw rainbow that fades across all pixels at once."""
        for j in range(256*iterations):
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColor(i, self.wheel((i+j) & 255))
            self.strip.show()
            time.sleep(wait_ms/1000.0)   

    def colourWipe(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0,0,0))
            self.strip.show()

    def startSeq(self, led):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0,0,0))
            self.strip.show()

        self.rainbow()
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0,0,0))
            self.strip.show()
        self.turnOnLED(led)
    
    def endSeq(self):
        self.rainbow()
        self.colourWipe()

str = Strip()
str.rainbow(1)
