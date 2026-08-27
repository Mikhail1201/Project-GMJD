"""
====================================================================
PROYECTO: SISTEMA DE MONITOREO AMBIENTAL - MONÓMEROS S.A.
MODULO: DRIVER I2C PARA PANTALLA LCD 16X2
LENGUAJE: MICROPYTHON
====================================================================
"""

import utime
from machine import I2C

# ==================================================================
# BLOQUE: CONTROLADOR HD44780 POR I2C (POO)
# ==================================================================
class I2cLcd:
    def __init__(self, i2c: I2C, i2c_addr: int, num_lines: int, num_columns: int):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.num_lines = num_lines
        self.num_columns = num_columns
        
        utime.sleep_ms(20)
        self._write_nibble(0x03)
        utime.sleep_ms(5)
        self._write_nibble(0x03)
        utime.sleep_us(100)
        self._write_nibble(0x03)
        self._write_nibble(0x02)
        
        self._send_command(0x28)
        self._send_command(0x0C)
        self._send_command(0x06)
        self.clear()

    def clear(self):
        self._send_command(0x01)
        utime.sleep_ms(2)

    def move_to(self, col: int, row: int):
        addr = col + (0x40 if row > 0 else 0)
        self._send_command(0x80 | addr)

    def putstr(self, string: str):
        for char in string:
            self._send_data(ord(char))

    def _write_nibble(self, nibble: int):
        byte = (nibble << 4) | 0x08
        self.i2c.writeto(self.i2c_addr, bytearray([byte | 0x04]))
        self.i2c.writeto(self.i2c_addr, bytearray([byte & ~0x04]))

    def _send_command(self, cmd: int):
        self._write_byte(cmd, 0)

    def _send_data(self, data: int):
        self._write_byte(data, 1)

    def _write_byte(self, byte: int, mode: int):
        high = (byte & 0xF0) | 0x08 | mode
        low = ((byte << 4) & 0xF0) | 0x08 | mode
        self.i2c.writeto(self.i2c_addr, bytearray([high | 0x04]))
        self.i2c.writeto(self.i2c_addr, bytearray([high & ~0x04]))
        self.i2c.writeto(self.i2c_addr, bytearray([low | 0x04]))
        self.i2c.writeto(self.i2c_addr, bytearray([low & ~0x04]))