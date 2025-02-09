#!/usr/bin/python
import spidev
import time
import pigpio
import time
import numpy as np
import scipy.fftpack
import time
import matplotlib.pyplot as plt


#Open SPI bus
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=1000000

#define custom chip select
#this is done so we can use dozens of SPI devices on 1 bus
CS_ADC = 12

SPI_BUS = 0  # SPI bus (0 or 1)
SPI_CS = 8   # Chip select GPIO pin (adjust as needed)
SAMPLE_FREQ = 50000  # ADC sampling frequency (samples per second)
WINDOW_SIZE = 2048   # Number of samples per FFT window
VREF = 3.3  # Reference voltage (adjust based on your ADC and system)
BIT_DEPTH = 12  # MCP3208 has a 12-bit resolution
POWER_THRESH = 9e-4 # tuning is activated if the signal power exceeds this threshold

# Set up pigpio and configure SPI settings
pi = pigpio.pi()  # Create an instance of pigpio
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

pi.spi_open(SPI_BUS, 1000000, 0)  # SPI speed: 1 MHz, mode: 0 (CPOL = 0, CPHA = 0)

def read_adc(channel):
    """Reads a value from the ADC using SPI with DMA"""
    # ADC command for MCP3208 (12-bit ADC)
    command = [0x06 | ((channel & 0x07) >> 2), ((channel & 0x03) << 6), 0x00]
    
    # Send the command to the ADC
    result = pi.spi_xfer(SPI_BUS, command)
    
    # Convert the result to 12-bit value
    value = (result[1][1] & 0x0F) << 8 | result[1][2]
    
    return value


def ConvertToVoltage(value, bitdepth, vref):
  return vref*(value/(2**bitdepth-1))

# Define delay between readings
delay = 0.5
 
while True:
    adc_value = read_adc(0)
    print(f"ADC Value: {adc_value}")
    voltage = ConvertToVoltage(adc_value, 12, 3.3) #for MCP3208 at 3.3V
    print(f"{voltage:.3f}")
    # Wait before repeating loop
    time.sleep(delay)
