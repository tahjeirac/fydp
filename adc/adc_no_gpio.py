#!/usr/bin/python
import spidev
import time


#Open SPI bus
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=1000000

#define custom chip select
#this is done so we can use dozens of SPI devices on 1 bus
CS_ADC = 12



#same thing but for the 12-bit MCP3208
def ReadChannel3208(channel):
  adc = spi.xfer2([6|(channel>>2),channel<<6,0]) #0000011x,xx000000,00000000
  data = ((adc[1]&15) << 8) + adc[2]
  return data

def ConvertToVoltage(value, bitdepth, vref):
  return vref*(value/(2**bitdepth-1))

# Define delay between readings
delay = 0.5
 
while True:
  value = ReadChannel3208(1)
  voltage = ConvertToVoltage(value, 12, 3.3) #for MCP3208 at 3.3V
  #print(value)
  print(f"{voltage:.3f}")
  # Wait before repeating loop
  time.sleep(delay)
