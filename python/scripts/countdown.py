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
This tool displays a countdown on the display.
Changing the display settings is not the scope of this program as there is another tool to do that.
"""

import argparse
import datetime
import time

from annax import MatrixError, MatrixGraphics, MatrixClient

DATETIME_FORMAT = "%d.%m.%Y %H:%M:%S"

def main():
    parser = argparse.ArgumentParser(description = "Countdown script")
    
    parser.add_argument('-s', '--server', type = str, required = True,
        help = "The server host to use for communication with the matrix controller")
    parser.add_argument('-p', '--port', type = int, default = 1810,
        help = "The server port to use for communication with the matrix controller (Default: 1810)")
    
    parser.add_argument('-d', '--displays', type = lambda x: tuple(map(int, x.split(","))), default = (),
        help = "The displays to send the message to")
    
    parser.add_argument('-t', '--target', type = str, required = True,
        help = "The target datetime to count down to, in the format %s" % DATETIME_FORMAT)
    parser.add_argument('-fmt', '--format', type = str, required = True,
        help = "A Python format string representing the desired text output (Example: '{hours:02d}h {minutes:02d}min left')")
    parser.add_argument('-tt', '--target-text', type = str, default = None,
        help = "A text to display once the countdown has finished")

    parser.add_argument('-f', '--font', type = str, default = "PixelMix",
        help = "The font name to use for rendering text (Default: PixelMix)")
    parser.add_argument('-fs', '--font-size', type = int, default = 8,
        help = "The font size to use for rendering text (Default: 8px)")
    parser.add_argument('-a', '--align', type = str, choices = ('left', 'center', 'right'), default = None,
        help = "How to align the text (useful only in static display mode; Default: Center)")

    args = parser.parse_args()
    
    if not args.displays:
        print("Warning: No displays selected.")

    client = MatrixClient(args.server, port = args.port)
    target = datetime.datetime.strptime(args.target, DATETIME_FORMAT)
    previous_countdown = ""

    try:
        while True:
            now = datetime.datetime.now()
            delta = target - now
            total_seconds = delta.total_seconds()
            if total_seconds < 0:
                if args.target_text:
                    client.append_text_message(args.displays, args.target_text, args.font, args.font_size, args.align)
                    client.commit()

                print("End of countdown, exiting.")
                break

            days, remainder = divmod(total_seconds, 60 * 60 * 24)
            hours, remainder = divmod(remainder, 60 * 60)
            minutes, remainder = divmod(remainder, 60)
            seconds = round(remainder)

            countdown = args.format.format(days = int(days), hours = int(hours), minutes = int(minutes), seconds = int(seconds), total_seconds = total_seconds)

            # Only update the display when necessary
            if countdown != previous_countdown:
                client.append_text_message(args.displays, countdown, args.font, args.font_size, args.align)
                client.commit()
                previous_countdown = countdown

            # Prevent CPU hogging
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("Exiting.")

if __name__ == "__main__":
    main()