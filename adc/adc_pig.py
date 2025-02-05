import pigpio
import time
import numpy as np
# Set up pigpio and configure SPI settings
pi = pigpio.pi()  # Create an instance of pigpio
if not pi.connected:
    print("Failed to connect to pigpio daemon!")
    exit()

SPI_BUS = 0  # SPI bus (0 or 1)
SPI_CS = 8   # Chip select GPIO pin (adjust as needed)

# Initialize SPI communication
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
    return vref * (value / (2 ** bitdepth - 1))
# Example: Read ADC value from channel 0

def ConvertToDB(value, bitdepth):
    return 20 * np.log10(value / (2 ** bitdepth - 1))
try:
    while True:
        adc_value = read_adc(0)
        print(f"ADC Value: {adc_value}")
        voltage = ConvertToVoltage(adc_value, 12, 3.3)  # For MCP3208 at 3.3V
        print(f"Voltage: {voltage} v")
        db_value = ConvertToDB(adc_value, 12)
        print(f"Volume in dB: {db_value} dB")
        time.sleep(0.001)

except KeyboardInterrupt:
    print("Program interrupted")

finally:
    pi.spi_close(SPI_BUS)
    pi.stop()
