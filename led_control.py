import time
from rpi_ws281x import *


# LED strip configuration:



class Strip:
    def __init__(self):
        self.LED_COUNT      = 8      # Number of LED pixels.
        self.LED_PIN        = 13      # GPIO pin connected to the pixels (18 uses PWM!).
        self.LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
        self.LED_DMA        = 10      # DMA channel to use for generating signal (try 10)
        self.LED_BRIGHTNESS = 65     # Set to 0 for darkest and 255 for brightest
        self.LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)
        self.LED_CHANNEL    = 1       # set to '1' for GPIOs 13, 19, 41, 45 or 53
        self.LAST = Color(0, 255, 0)
        self.LED_ON = -1
        self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ, self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
        self.strip.begin()


    def blinkLED(self, led):
        self.strip.setPixelColor(led, Color(255, 0, 0))
        self.strip.show()
        time.sleep(0.5)
        self.strip.setPixelColor(led, Color(0,0,0))
        self.strip.show()
        time.sleep(0.5)

    def turnOnLED(self, led):
        c = Color(0, 255, 0)
        print (led)
        if self.LED_ON != -1:
            self.strip.setPixelColor(self.LED_ON, Color(0,0,0))
            self.strip.show()
        if self.LED_ON == led:
            if self.LAST == Color(0, 255, 0):
                c = Color(0, 0, 255)
                self.LAST =  Color(0, 0, 255)
            else:
                c =  Color(0, 255, 0)
                self.LAST =  Color(0, 255, 0)
        self.strip.setPixelColor(led, c)
        self.strip.show()
        self.LED_ON = led

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