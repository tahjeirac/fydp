#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = "Thomas Kaulke"
__email__ = "kaulketh@gmail.com"

import gpiozero
import spidev

_MIN_CHANNEL = 0
_MAX_CHANNEL = 7


def _check_channel_range(channel: int, min_ch: int, max_ch: int):
    """
    Number of channels to read from ADC:\n
    MCP3004: 4 channels, min=0 max=3\n
    MCP3008: 8 channels, min=0 max=7\n
    MCP3204: 4 channels, min=0 max=3\n
    MCP3208: 8 channels, min=0 max=7\n
    """
    if channel not in range(min_ch, max_ch + 1, 1):
        raise Exception(f"Channel must be {min_ch}-{max_ch}: {channel}?")


class MCP3208Gpiozero:
    # [skip pep8] ignore=E501
    # noinspection LongLine
    """
    using gpiozero SPI device,
    GPIO Zero: a library for controlling the Raspberry Pi's GPIO pins

    https://gpiozero.readthedocs.io/en/v1.2.0/_modules/gpiozero/spi_devices.html#MCP3208
    https://gpiozero.readthedocs.io/en/v1.2.0/api_spi.html#gpiozero.MCP3208
    """

    def __init__(self, port: int = 0, device: int = 0):
        self.__device = device
        self.__port = port

    @property
    def info(self):
        return f"ID:{id(self)} {self.__repr__()}"

    def read(self, channel):
        """
        Read input channel of MCP3208

        :param channel: 0-7 (D0 - D7 of MCP3208)
        :return: raw data value (12bit 0 - 4095)
        """
        _check_channel_range(channel, _MIN_CHANNEL, _MAX_CHANNEL)
        return gpiozero.MCP3208(channel,
                                differential=False,
                                max_voltage=3.3,
                                port=self.__port,
                                device=self.__device).raw_value


class MCP3208Spidev:
    """
    using built-in module spidev
    """

    def __init__(self, port: int = 0, device: int = 0, speed: int = 500_000):
        # [skip pep8] ignore=E501
        # noinspection LongLine
        """

        :param device: RaspberryPi chip set CE0 BCM8 (GPIO8) PIN24 or CE1 BCM7 (GPIO7) PIN26, CE0 per default
        :param speed: Maximum speed in Hz, 1 MHz per default
        """
        self.__speed = speed
        self.__device = device
        self.__bus = port
        self.__adc = 0
        self.__data = 0
        self.__spi = spidev.SpiDev()
        self.__spi.open(self.__bus, self.__device)
        self.__spi.max_speed_hz = self.__speed

    def __del__(self):
        self.__spi.close()

    @property
    def info(self):
        return f"ID:{id(self)} {self.__repr__()}"

    def read(self, channel: int):
        """
        Read input channel of MCP3208\n
        https://www.vampire.de/index.php/2018/05/06/raspberry-pi-mit-mcp3208/

        :param channel: 0-7 (D0 - D7 of MCP3208)
        :return: raw data value (12bit 0 - 4095)
        """
        _check_channel_range(channel, _MIN_CHANNEL, _MAX_CHANNEL)

        self.__adc = self.__spi.xfer2(
            [
                6 | (channel & 4) >> 2,
                (channel & 3) << 6,
                0
            ])
        self.__data = ((self.__adc[1] & 15) << 8) + self.__adc[2]
        return self.__data


if __name__ == '__main__':
    pass