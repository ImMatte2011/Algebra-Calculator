import time
from machine import I2C
from drivers.lcd_api import LcdApi

class I2cLcd(LcdApi):
    def __init__(self, i2c, i2c_addr, num_lines, num_columns):
        self.i2c = i2c
        self.i2c_addr = i2c_addr
        self.i2c.writeto(self.i2c_addr, bytes([0]))
        time.sleep_ms(20)
        self.hal_write_init_nibble(0x30)
        time.sleep_ms(5)
        self.hal_write_init_nibble(0x30)
        time.sleep_ms(1)
        self.hal_write_init_nibble(0x30)
        self.hal_write_init_nibble(0x20)
        self.hal_write_command(0x20 | 0x08)
        self.hal_write_command(0x0C | 0x00)
        self.hal_write_command(0x06)
        self.clear()
        self.hal_write_command(0x0C | 0x04)

    def hal_write_init_nibble(self, nibble):
        byte = (nibble & 0xF0) | 0x04
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        time.sleep_ms(1)
        byte &= 0xFB
        self.i2c.writeto(self.i2c_addr, bytes([byte]))

    def hal_write_command(self, cmd):
        byte = (cmd & 0xF0) | 0x04
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        byte &= 0xFB
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        byte = ((cmd << 4) & 0xF0) | 0x04
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        byte &= 0xFB
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        if cmd <= 2:
            time.sleep_ms(5)

    def hal_write_data(self, data):
        byte = (data & 0xF0) | 0x05
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        byte &= 0xFB
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        byte = ((data << 4) & 0xF0) | 0x05
        self.i2c.writeto(self.i2c_addr, bytes([byte]))
        byte &= 0xFB
        self.i2c.writeto(self.i2c_addr, bytes([byte]))