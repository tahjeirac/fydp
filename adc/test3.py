import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import platform
import spidev # To communicate with SPI devices
from time import sleep	# To add delay
import RPi.GPIO as GPIO	# To use GPIO pins

# Start SPI connection
spi = spidev.SpiDev()  # Created an object
spi.open(0, 0)  # Open SPI bus 0, device 0 (MCP3208)

GPIO.setmode(GPIO.BCM)

print("Python version: " + platform.python_version())
print("matplotlib version: " + mpl.__version__)

# Set up plot
fig, ax = plt.subplots()
line, = ax.plot(np.random.rand(10))
ax.set_ylim(0, 4095)  # MCP3208 is a 12-bit ADC, so max value is 4095
xdata, ydata = [0]*100, [0]*100

# Read MCP3208 data (12-bit ADC)
def analogInput(channel):
    # Send start bit, single-ended bit, and channel
    # MCP3208 uses 3 bits for the channel (0 to 7), so we shift accordingly
    spi.max_speed_hz = 1350000  # SPI clock rate
    # Send 3-byte sequence to read data from the selected channel
    adc = spi.xfer2([0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00])
    # The result is returned as a 12-bit number, combining the received bytes
    data = ((adc[1] & 0x0F) << 8) | adc[2]
    return data

# Update plot with new data
def update(data):
    line.set_ydata(data)
    return line,

# Main function to handle plotting and data update
def run(data):
    global xdata, ydata
    x, y = data
    if x == 0:
        xdata = [0] * 100
        ydata = [0] * 100
    del xdata[0]
    del ydata[0]
    xdata.append(x)
    ydata.append(y)
    line.set_data(xdata, ydata)
    return line,

# Data generator
def data_gen():
    x = 9
    while True:
        if x >= 9:
            x = 0
        else:
            x += 0.1
            
        try:
            inRaw = analogInput(0)  # Reading from channel 0 (can change as needed)
            sleep(0.02)  # Delay for sample rate control
            inInt = int(inRaw)
        except:
            inInt = 0
        
        yield x, inInt

# Animate the plot
ani = animation.FuncAnimation(fig, run, data_gen, interval=0, blit=True)
plt.show()
