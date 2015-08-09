#!/usr/bin/env python3
# Copyright 2015 Julian Metzler

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
This file contains utilities for generating text, graphics and other useful stuff that goes beyond
the pure matrix controller functions.
"""

import re
import subprocess

from PIL import Image, ImageDraw, ImageFont

# A few pre-compiled bitmaps with various patterns
BITMAP_CHECKER = [
    [0, 1] * 60,
    [1, 0] * 60,
    [0, 1] * 60,
    [1, 0] * 60,
    [0, 1] * 60,
    [1, 0] * 60,
    [0, 1] * 60,
    [1, 0] * 60
]

BITMAP_CHECKER_INVERTED = [
    [1, 0] * 60,
    [0, 1] * 60,
    [1, 0] * 60,
    [0, 1] * 60,
    [1, 0] * 60,
    [0, 1] * 60,
    [1, 0] * 60,
    [0, 1] * 60
]

BITMAP_FULL = [
    [1] * 120,
    [1] * 120,
    [1] * 120,
    [1] * 120,
    [1] * 120,
    [1] * 120,
    [1] * 120,
    [1] * 120
]

BITMAP_EMPTY = [
    [0] * 120,
    [0] * 120,
    [0] * 120,
    [0] * 120,
    [0] * 120,
    [0] * 120,
    [0] * 120,
    [0] * 120
]

class MatrixGraphics(object):
    def __init__(self, controller, debug = False):
        self.debug = debug
        self.controller = controller
        self.font_list = {}
        self.load_fonts()
    
    def load_fonts(self):
        def _parse_line(line):
            try:
                path, name, style = [part.strip() for part in line.split(":")]
            except ValueError:
                return (None, None)
            style = style.lower()
            styles = []
            if "bold" in style:
                styles.append("Bold")
            if "italic" in style:
                styles.append("Italic")
            if "narrow" in style:
                styles.append("Narrow")
            if "regular" in style:
                styles.append("Regular")
            if "oblique" in style:
                styles.append("Oblique")
            if "condensed" in style:
                styles.append("Condensed")
            if "black" in style:
                styles.append("Black")
            combined_name = name + " " + " ".join(styles)
            return (path, combined_name)
        
        if self.debug:
            print("Loading available fonts...")

        raw_list = subprocess.check_output(("fc-list", "-f", "%{file}:%{family}:%{style}\n", ":fontformat=TrueType")).decode('utf-8')
        font_list = dict([_parse_line(line) for line in raw_list.splitlines()])
        for path, name in font_list.items():
            if path and name:
                self.font_list[name.lower()] = path

        if self.debug:
            print("Found %i fonts:\n%s" % (len(self.font_list), "\n".join(["- " + name.title() for name in sorted(self.font_list.keys())])))
    
    def get_font(self, query):
        query = query.lower()
        # Perform a direct lookup first
        path = self.font_list.get(query)
        if path:
            return path
        # Then check for a font called "... regular"
        path = self.font_list.get(query + " regular")
        if path:
            return path
        # Finally, get all partial matches...
        candidates = []
        for name in self.font_list:
            if query in name or name in query:
                candidates.append((name, self.font_list[name]))
        # ...and return the one with the shortest name
        if candidates:
            candidates.sort(key = lambda x:len(x[0]))
            return candidates[0][1]
        else:
            return None
    
    def image_to_long_bitmap(self, image):
        # Convert an image to a bitmap where pixels are represented as an array of 1 and 0
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        
        long_bitmap = []
        pixels = image.load()
        width, height = image.size
        for y in range(height):
            row = []
            for x in range(width):
                pixel = pixels[x, y]
                row.append(int(pixel[:3] != (0, 0, 0))) # 0 (black) or 1 (any other color)
            long_bitmap.append(row)
        
        return long_bitmap
    
    def image_to_short_bitmap(self, image):
        # Convert an image to a bitmap where pixels are represented as 8-bit integers in groups of 8
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        
        short_bitmap = []
        temp_bitmap = []
        data = "".join(map(str, [int(pixel[:3] != (0, 0, 0)) for pixel in image.getdata()]))
        width, height = image.size
        rows = [data[i:i + width] for i in range(0, len(data), width)]
        for row in rows:
            short_row = []
            # Iterate over the string in chunks of 8
            cur_x_pos = 0
            while cur_x_pos < len(row):
                # Convert the current chunk into an 8-bit value
                chunk = row[cur_x_pos:cur_x_pos + 8].ljust(8, "0")
                short_row.append(int(chunk, 2))
                cur_x_pos += 8
            temp_bitmap.append(short_row)
        
        for x in range(len(temp_bitmap[0])):
            new_block = []
            for y in range(height):
                new_block.append(temp_bitmap[y][x])
            short_bitmap.append(new_block)
        return short_bitmap
    
    def long_bitmap_to_short_bitmap(self, long_bitmap):
        # Convert a "long-form" bitmap to a "short-form" bitmap
        short_bitmap = []
        temp_bitmap = []
        for row in long_bitmap:
            short_row = []
            # Turn the row into a string of 1 and 0
            row_str = "".join(map(str, row))
            # Iterate over the string in chunks of 8
            cur_x_pos = 0
            while cur_x_pos < len(row_str):
                # Convert the current chunk into an 8-bit value
                chunk = row_str[cur_x_pos:cur_x_pos + 8].ljust(8, "0")
                short_row.append(int(chunk, 2))
                cur_x_pos += 8
            temp_bitmap.append(short_row)
        
        for x in range(len(temp_bitmap[0])):
            new_block = []
            for y in range(len(long_bitmap)):
                new_block.append(temp_bitmap[y][x])
            short_bitmap.append(new_block)
        return short_bitmap
    
    def align_image(self, image, align):
        if not isinstance(image, Image.Image):
            image = Image.open(image)
        
        if align == 'left':
            aligned_image = Image.new('RGB', (self.controller.num_blocks * 8, 8), (0, 0, 0))
            aligned_image.paste(image, (0, 0))
        elif align == 'center':
            aligned_image = Image.new('RGB', (self.controller.num_blocks * 8, 8), (0, 0, 0))
            aligned_image.paste(image, (int((aligned_image.size[0] - image.size[0]) / 2), 0))
        elif align == 'right':
            aligned_image = Image.new('RGB', (self.controller.num_blocks * 8, 8), (0, 0, 0))
            aligned_image.paste(image, (aligned_image.size[0] - image.size[0], 0))
        else:
            aligned_image = image
        
        return aligned_image
    
    def align_long_bitmap(self, long_bitmap, align):
        bitmap_width = len(long_bitmap[0])
        target_width = self.controller.num_blocks * 8
        
        if bitmap_width == target_width:
            pass
        elif bitmap_width < target_width:
            if align == 'left':
                for i in range(len(long_bitmap)):
                    long_bitmap[i] += [0] * (target_width - bitmap_width)
            elif align == 'center':
                for i in range(len(long_bitmap)):
                    long_bitmap[i] = [0] * int((target_width - bitmap_width) / 2) + long_bitmap[i]
                    long_bitmap[i] += [0] * (int((target_width - bitmap_width) / 2) + bitmap_width % 2)
            elif align == 'right':
                for i in range(len(long_bitmap)):
                    long_bitmap[i] = [0] * (target_width - bitmap_width) + long_bitmap[i]
            else:
                pass
        elif bitmap_width > target_width:
            if align == 'left':
                for i in range(len(long_bitmap)):
                    long_bitmap[i] = long_bitmap[i][:target_width]
            elif align == 'center':
                for i in range(len(long_bitmap)):
                    long_bitmap[i] = long_bitmap[i][int(target_width / 2):][:-(int(target_width / 2) - bitmap_width % 2)]
            elif align == 'right':
                for i in range(len(long_bitmap)):
                    long_bitmap[i] = long_bitmap[i][-target_width:]
            else:
                pass
        
        return long_bitmap
    
    def build_image(self, image, align = None):
        aligned_image = self.align_image(image, align)
        return self.image_to_long_bitmap(aligned_image)
    
    def send_image(self, image, align = None):
        aligned_image = self.align_image(image, align)
        return self.controller.send_bitmap(self.image_to_short_bitmap(aligned_image))
    
    def _prepare_text(self, text, font = "sans", size = 11):
        """
        Images can be embedded in the text like this:
            Here's an embedded image: @img:</path/to/image.png> It looks nice, doesn't it?
        """
        
        modified_text = re.sub(r"@img:<.+?>", "\x00", text)
        paths = [match.groupdict()['path'] for match in re.finditer(r".*?@img:<(?P<path>.+?)>.*?", text)] + [None]
        data = [('text', part) for part in modified_text.split("\x00")]
        data = [x for t in zip(data, [('image', path) for path in paths]) for x in t]
        
        font_path = self.get_font(font)
        font = ImageFont.truetype(font_path, size)

        # Calculate the base height of the font in order to get the alignment right
        # Also, font.getsize() seems to be unreliable so we have to go a bit further
        TEST_TEXT = "GgFf"
        approx_base_size = font.getsize(TEST_TEXT)
        test_image = Image.new("RGB", approx_base_size, (0, 0, 0))
        test_draw = ImageDraw.Draw(test_image)
        test_draw.fontmode = "1"
        test_draw.text((0, 0), TEST_TEXT, (255, 255, 255), font = font)
        base_left, base_top, base_right, base_bottom = test_image.getbbox()
        base_height = base_bottom - base_top
        top_offset = 8 - base_height

        images = []
        for what, value in data:
            if not value:
                continue
            
            if what == 'text':
                width, height = font.getsize(value)
                image = Image.new('RGB', (width, height + top_offset), (0, 0, 0))
                draw = ImageDraw.Draw(image)
                draw.fontmode = "1" # Turn off antialiasing by setting the color mode to bilevel
                draw.text((0, top_offset), value, (255, 255, 255), font = font)
                # Auto-crop the text image because the calculated size isn't always correct
                actual_left, actual_top, actual_right, actual_bottom = image.getbbox()
                actual_height = actual_bottom - actual_top
                corrected_top = actual_top - top_offset
                image = image.crop((actual_left, corrected_top, actual_right, actual_bottom))
                images.append(image)
            elif what == 'image':
                images.append(Image.open(value))
        
        total_width = sum(map(lambda img: img.size[0], images))
        complete_image = Image.new('RGB', (total_width, 8), (0, 0, 0))
        
        cur_x_pos = 0
        for image in images:
            complete_image.paste(image, (cur_x_pos, 0))
            cur_x_pos += image.size[0]
        
        return complete_image
    
    def build_text(self, text, font = "sans", size = 11, align = None):
        image = self._prepare_text(text, font, size)
        return self.image_to_long_bitmap(self.align_image(image, align))
    
    def send_text(self, text, font = "sans", size = 11, align = None):
        image = self._prepare_text(text, font, size)
        return self.controller.send_bitmap(self.image_to_short_bitmap(self.align_image(image, align)))
    
    def send_long_bitmap(self, bitmap, align = None):
        new_bitmap = self.align_long_bitmap(bitmap, align)
        return self.controller.send_bitmap(self.long_bitmap_to_short_bitmap(new_bitmap))
    
    def blend_long_bitmaps(self, bitmap1, bitmap2):
        if len(bitmap1[0]) >= len(bitmap2[0]):
            base = bitmap1
            top = bitmap2
        else:
            base = bitmap2
            top = bitmap1
        
        new_bitmap = []
        for y in range(len(base)):
            row = []
            for x in range(len(base[0])):
                if x < len(top[0]):
                    row.append(base[y][x] or top[y][x])
                else:
                    row.append(base[y][x])
            new_bitmap.append(row)
        return new_bitmap