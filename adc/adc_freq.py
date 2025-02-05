#!/usr/bin/python
import spidev
import time
import RPi.GPIO as GPIO
import numpy as np

# Setup SPI and GPIO
GPIO.setmode(GPIO.BCM)
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000

CS_ADC = 12
GPIO.setup(CS_ADC, GPIO.OUT)

# Read from MCP3208 (12-bit ADC)
def ReadChannel3208(channel):
    adc = spi.xfer2([6 | (channel >> 2), channel << 6, 0]) # 0000011x,xx000000,00000000
    data = ((adc[1] & 15) << 8) + adc[2]
    return data

# Sampling Parameters
SAMPLE_RATE = 10000  # 10 kHz sampling rate
NUM_SAMPLES = 1024   # Power of 2 for FFT

# Function to calculate frequency from ADC samples
def get_frequency(samples, sample_rate):
    # Remove DC offset
    samples = np.array(samples) - np.mean(samples)

    # Apply FFT
    fft_result = np.fft.fft(samples)
    freqs = np.fft.fftfreq(len(samples), 1/sample_rate)

    # Get dominant frequency
    magnitude = np.abs(fft_result)
    peak_idx = np.argmax(magnitude[:len(magnitude)//2])  # Ignore negative frequencies
    return freqs[peak_idx]

while True:
    samples = []
    
    # Collect ADC samples
    start_time = time.time()
    for _ in range(NUM_SAMPLES):
        GPIO.output(CS_ADC, GPIO.LOW)
        value = ReadChannel3208(1)  # Read from mic channel
        GPIO.output(CS_ADC, GPIO.HIGH)
        samples.append(value)
        time.sleep(1/SAMPLE_RATE)  # Control sample rate
    
    # Calculate and print frequency
    frequency = get_frequency(samples, SAMPLE_RATE)
    print(f"Detected Frequency: {frequency:.2f} Hz")

    # Ensure consistent sampling intervals
    elapsed_time = time.time() - start_time
    time.sleep(max(0, (NUM_SAMPLES / SAMPLE_RATE) - elapsed_time))
