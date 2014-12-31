#!/usr/bin/env python3
# Copyright 2014 Julian Metzler

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

import re
import serial
import time

from PIL import Image, ImageDraw, ImageFont

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
		if not code:
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
	def __init__(self, port, baudrate = 57600, num_blocks = 15, max_tries = 5, retry_delay = 0.2):
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
	
	def send_image(self, image, align = None):
		if not isinstance(image, Image.Image):
			image = Image.open(image)
		
		if align == 'left':
			_image = Image.new('RGB', (self.num_blocks * 8, 8), (0, 0, 0))
			_image.paste(image, (0, 0))
		elif align == 'center':
			_image = Image.new('RGB', (self.num_blocks * 8, 8), (0, 0, 0))
			_image.paste(image, (int((_image.size[0] - image.size[0]) / 2), 0))
		elif align == 'right':
			_image = Image.new('RGB', (self.num_blocks * 8, 8), (0, 0, 0))
			_image.paste(image, (_image.size[0] - image.size[0], 0))
		elif align is None:
			_image = image
		
		data = list(_image.getdata())
		seq = ["0" if pixel[:3] == (0, 0, 0) else "1" for pixel in data]
		pixels = []
		cols, rows = _image.size
		cur_index = 0
		
		while cur_index < len(data):
			cur_row = seq[cur_index:cur_index + cols]
			cur_x_pos = 0
			new_row = []
			
			while cur_x_pos < len(cur_row):
				new_row.append(int("".join(cur_row[cur_x_pos:cur_x_pos + 8]).ljust(8, "0"), 2))
				cur_x_pos += 8
			
			pixels.append(new_row)
			cur_index += cols
		
		bitmap = []
		for x in range(len(pixels[0])):
			new_block = []
			for y in range(rows):
				new_block.append(pixels[y][x])
			
			bitmap.append(new_block)
		
		return self.send_bitmap(bitmap)
	
	def send_text(self, text, font = "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf", size = 11, align = None):
		modified_text = re.sub(r"@img:<.+?>", "\x00", text)
		paths = [match.groupdict()['path'] for match in re.finditer(r".*?@img:<(?P<path>.+?)>.*?", text)] + [None]
		data = [('text', part) for part in modified_text.split("\x00")]
		data = [x for t in zip(data, [('image', path) for path in paths]) for x in t]
		
		font = ImageFont.truetype(font, size)
		images = []
		for what, value in data:
			if not value:
				continue
			
			if what == 'text':
				width, height = font.getsize(value)
				image = Image.new('RGB', (width, 8), (0, 0, 0))
				draw = ImageDraw.Draw(image)
				draw.fontmode = "1" # Turn off antialiasing
				draw.text((0, round((8 - height) / 2) - 1), value, (255, 255, 255), font = font)
				images.append(image)
			elif what == 'image':
				images.append(Image.open(value))
		
		total_width = sum(map(lambda img: img.size[0], images))
		complete_image = Image.new('RGB', (total_width, 8), (0, 0, 0))
		
		cur_x_pos = 0
		for image in images:
			complete_image.paste(image, (cur_x_pos, 0))
			cur_x_pos += image.size[0]
		
		return self.send_image(complete_image, align = align)
	
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
		
		return self.set_parameter(1, mode)
	
	def set_scroll_speed(self, speed):
		return self.set_parameter(2, speed)
	
	def set_scroll_direction(self, direction):
		"""
		0: Left
		1: Right
		"""
		
		return self.set_parameter(3, direction)
	
	def set_scroll_mode(self, mode):
		"""
		0: Repeat on visibility of end
		1: Repeat on disappearance
		2: Repeat after gap
		"""
		
		return self.set_parameter(4, mode)
	
	def set_scroll_gap(self, gap):
		return self.set_parameter(5, gap)
	
	def set_power_state(self, state):
		"""
		0: Off
		1: On
		"""
		
		return self.set_parameter(6, state)
	
	def set_blink_frequency(self, frequency):
		return self.set_parameter(7, frequency)
	
	def set_stop_indicator(self, state):
		"""
		0: Off
		1: On
		"""
		
		return self.set_parameter(8, state)