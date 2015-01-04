#!/usr/bin/env python3
# Copyright 2014-2015 Julian Metzler

"""
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

"""
This file contains the classes needed to address the matrix controller board in the display itself.
"""

import serial
import time

from PIL import Image

class MatrixError(Exception):
    ERR_CODES = {
        -1: "Unknown error",
        0: "Invalid action byte",
        1: "Invalid intermediate byte #1",
        2: "Invalid block count",
        3: "Invalid intermediate byte #2",
        4: "Timeout while receiving bitmap data",
        5: "Invalid bitmap data",
        6: "Invalid value for selected option",
        31: "Serial communication successful" # Just in case, this equals the response 0xFF indicating success
    }
    
    def __init__(self, code = None, response = None):
        if code is None:
            if response:
                self.code = response - 0xE0
            else:
                self.code = -1
        else:
            self.code = code
        
        self.description = self.ERR_CODES.get(self.code, None)
    
    def __str__(self):
        return "%i: %s" % (self.code, self.description)

class MatrixController(object):
    def __init__(self, port, baudrate = 115200, num_blocks = 15, max_tries = 10, retry_delay = 0.1):
        self.port = serial.serial_for_url(port, baudrate = baudrate)
        self.num_blocks = num_blocks
        self.max_tries = max_tries
        self.retry_delay = retry_delay
    
    def send_raw_datagram(self, datagram):
        num_tries = 0
        success = False
        while num_tries < self.max_tries and not success:
            if num_tries > 0:
                time.sleep(self.retry_delay)
            
            self.port.write(datagram)
            time.sleep(0.1)
            response = ord(self.port.read(1))
            success = response == 0xFF
            num_tries += 1
        
        if not success:
            raise MatrixError(response = response)
        
        return True
    
    def send_bitmap(self, bitmap):
        datagram = bytearray()
        datagram.append(0xFF)
        datagram.append(0xA0)
        datagram.append(0xCC)
        datagram.append(len(bitmap))
        datagram.append(0xCC)
        
        for block in bitmap:
            for byte in block:
                datagram.append(byte)
        
        return self.send_raw_datagram(datagram)
    
    def set_parameter(self, code, value):
        """
        Example: set_parameter(3, 20) would set parameter 0xA3 to the value 0x14
        """
        
        assert 0x01 <= code <= 0x0F
        assert 0x00 <= value <= 0xFF
        
        datagram = bytearray()
        datagram.append(0xFF)
        datagram.append(0xA0 + code)
        datagram.append(0xCC)
        datagram.append(value)
        
        return self.send_raw_datagram(datagram)
    
    def set_display_mode(self, mode):
        """
        0: Static
        1: Scrolling
        """
        
        if not isinstance(mode, int):
            mode = ('static', 'scroll').index(mode)
        
        return self.set_parameter(1, mode)
    
    def set_scroll_speed(self, speed):
        return self.set_parameter(2, speed)
    
    def set_scroll_direction(self, direction):
        """
        0: Left
        1: Right
        """
        
        if not isinstance(direction, int):
            direction = ('left', 'right').index(direction)
        
        return self.set_parameter(3, direction)
    
    def set_scroll_mode(self, mode):
        """
        0: Repeat on visibility of end
        1: Repeat on disappearance
        2: Repeat after gap
        """
        
        if not isinstance(mode, int):
            mode = ('repeat-on-end', 'repeat-on-disappearance', 'repeat-after-gap').index(mode)
        
        return self.set_parameter(4, mode)
    
    def set_scroll_gap(self, gap):
        return self.set_parameter(5, gap)
    
    def set_power_state(self, state):
        """
        0: Off
        1: On
        """
        
        if not isinstance(state, int):
            state = ('off', 'on').index(state)
        
        return self.set_parameter(6, state)
    
    def set_blink_frequency(self, frequency):
        return self.set_parameter(7, frequency)
    
    def set_stop_indicator(self, state):
        """
        0: Off
        1: On
        """
        
        if not isinstance(state, int):
            state = ('off', 'on').index(state)
        
        return self.set_parameter(8, state)