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
This script is a tool to control a directly connected matrix controller board from the command line.
"""

import argparse
import serial
import sys
import time

from matrix_controller import MatrixController, MatrixError
from matrix_graphics import MatrixGraphics

def main():
    parser = argparse.ArgumentParser(description = "Command-line control script for a matrix controller")
    parser.add_argument('-p', '--port', type = str, default = "/dev/ttyACM0",
        help = "The serial port to use for communication with the matrix controller (Default: /dev/ttyACM0)")
    parser.add_argument('-b', '--baudrate', type = int, default = 57600,
        help = "The baudrate to use for communication with the matrix controller (Default: 57600)")
    
    parser.add_argument('-i', '--image', type = str, default = None,
        help = "An image to load into the matrix (black = pixel off, any other color = pixel on)")
    parser.add_argument('-t', '--text', type = str, default = None,
        help = "A text to write to the matrix, rendered with the specified TrueType font")
    parser.add_argument('-f', '--font', type = str, default = "Arial",
        help = "The TrueType font (file path) to use for rendering text (Default: Arial)")
    parser.add_argument('-s', '--font-size', type = int, default = 11,
        help = "The font size to use for rendering text (Default: 11)")
    parser.add_argument('-a', '--align', type = str, choices = ('left', 'center', 'right'), default = None,
        help = "How to align the text or image (useful only in static display mode)")
    
    parser.add_argument('-dm', '--display-mode', type = str, choices = ('static', 'scroll', 'auto'), default = None,
        help = "How to display the text")
    parser.add_argument('-ss', '--scroll-speed', type = int, default = None,
        help = "How many frames should pass before advancing the scrolling text (slower values = faster scrolling)")
    parser.add_argument('-sd', '--scroll-direction', type = str, choices = ('left', 'right'), default = None,
        help = "The direction to scroll the text in")
    parser.add_argument('-sm', '--scroll-mode', type = str, choices = ('repeat-on-end', 'repeat-on-disappearance', 'repeat-after-gap'), default = None,
        help = "How the scrolling text should behave. (Repeat as soon as the end of the text is visible, as soon as it has completely disappeared or after the specified number of empty blocks has passed)")
    parser.add_argument('-sg', '--scroll-gap', type = int, default = None,
        help = "The number of empty blocks that should pass before the scrolling text is repeated (1 block = 8 pixels)")
    parser.add_argument('-ps', '--power-state', type = str, choices = ('on', 'off'), default = None,
        help = "Enable or disable the display")
    parser.add_argument('-bf', '--blink-frequency', type = int, default = None,
        help = "The frame count until the display blink state should be toggled")
    parser.add_argument('-si', '--stop-indicator', type = str, choices = ('on', 'off'), default = None,
        help = "Enable or disable the stop indicator")
    parser.add_argument('-sst', '--scroll-step', type = int, default = None,
        help = "How many pixels a scrolling text should be shifted each frame (higher values = faster scrolling)")
    parser.add_argument('-sbf', '--stop-indicator-blink-frequency', type = int, default = None,
        help = "The frame count until the stop indicator blink state should be toggled")

    args = parser.parse_args()
    
    controller = MatrixController(args.port, baudrate = args.baudrate)
    
    if args.image is not None:
        graphics = MatrixGraphics(controller)
        graphics.send_image(args.image, align = args.align)
    elif args.text is not None:
        graphics = MatrixGraphics(controller)
        graphics.send_text(args.text, font = args.font, size = args.font_size, align = args.align)
    
    if args.display_mode is not None:
        if args.display_mode == 'static':
            mode = 0
        elif args.display_mode == 'scroll':
            mode = 1
        elif args.display_mode == 'auto':
            mode = 2
        
        controller.set_display_mode(mode)
    
    if args.scroll_speed is not None:
        controller.set_scroll_speed(args.scroll_speed)
    
    if args.scroll_direction is not None:
        if args.scroll_direction == 'left':
            direction = 0
        elif args.scroll_direction == 'right':
            direction = 1
        
        controller.set_scroll_direction(direction)
    
    if args.scroll_mode is not None:
        if args.scroll_mode == 'repeat-on-end':
            mode = 0
        elif args.scroll_mode == 'repeat-on-disappearance':
            mode = 1
        elif args.scroll_mode == 'repeat-after-gap':
            mode = 2
        
        controller.set_scroll_mode(mode)
    
    if args.scroll_gap is not None:
        controller.set_scroll_gap(args.scroll_gap)
    
    if args.power_state is not None:
        if args.power_state == 'off':
            state = 0
        elif args.power_state == 'on':
            state = 1
        
        controller.set_power_state(state)
    
    if args.blink_frequency is not None:
        controller.set_blink_frequency(args.blink_frequency)
    
    if args.stop_indicator is not None:
        if args.stop_indicator == 'off':
            state = 0
        elif args.stop_indicator == 'on':
            state = 1
        
        controller.set_stop_indicator(state)
    
    if args.scroll_step is not None:
        controller.set_scroll_step(args.scroll_step)
    
    if args.stop_indicator_blink_frequency is not None:
        controller.set_stop_indicator_blink_frequency(args.stop_indicator_blink_frequency)

if __name__ == "__main__":
    main()