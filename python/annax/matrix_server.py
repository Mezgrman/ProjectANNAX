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
This file contains the classes needed to operate a server which controls four matrix displays.
The server operates on a simple JSON-based protocol. The full protocol specification can be found
in the SERVER_PROTOCOL.md file.
The server runs as two threads; one to listen for messages and one to control the displays.
"""

import datetime
import json
import socket
import threading
import time
import traceback

from .matrix_graphics import MatrixGraphics

def receive_message(sock):
    # Receive and parse an incoming message (prefixed with its length)
    try:
        length = int(sock.recv(5))
        raw_data = sock.recv(length)
        message = json.loads(raw_data.decode('utf-8'))
    except:
        raise
    return message

def send_message(sock, data):
    # Build and send a message (prefixed with its length)
    raw_data = json.dumps(data)
    length = len(raw_data)
    message = "%05i%s" % (length, raw_data)
    sock.sendall(message.encode('utf-8'))

def discard_message(sock):
    sock.setblocking(False)
    try:
        while True:
            sock.recv(1024)
    except socket.error:
        pass
    finally:
        sock.setblocking(True)

class MatrixServer(object):
    # This stores the actual bitmap that is displayed at the moment. Written exclusively by the display thread.
    CURRENT_BITMAP = [
        None,
        None,
        None,
        None
    ]
    
    # This stores the messages that should be displayed. Written exclusively by the message thread.
    CURRENT_MESSAGE = [
        None,
        None,
        None,
        None
    ]
    
    # This stores the current controller settings for each display.
    CURRENT_CONFIG = [
        {
            'display_mode': 'static',
            'scroll_speed': 1,
            'scroll_direction': 'left',
            'scroll_mode': 'repeat-on-disappearance',
            'scroll_gap': 5,
            'power_state': 'off',
            'blink_frequency': 0,
            'stop_indicator': 'off',
            'scroll_step': 1,
            'stop_indicator_blink_frequency': 0
        },
        {
            'display_mode': 'static',
            'scroll_speed': 1,
            'scroll_direction': 'left',
            'scroll_mode': 'repeat-on-disappearance',
            'scroll_gap': 5,
            'power_state': 'off',
            'blink_frequency': 0,
            'stop_indicator': 'off',
            'scroll_step': 1,
            'stop_indicator_blink_frequency': 0
        },
        {
            'display_mode': 'static',
            'scroll_speed': 1,
            'scroll_direction': 'left',
            'scroll_mode': 'repeat-on-disappearance',
            'scroll_gap': 5,
            'power_state': 'off',
            'blink_frequency': 0,
            'stop_indicator': 'off',
            'scroll_step': 1,
            'stop_indicator_blink_frequency': 0
        },
        {
            'display_mode': 'static',
            'scroll_speed': 1,
            'scroll_direction': 'left',
            'scroll_mode': 'repeat-on-disappearance',
            'scroll_gap': 5,
            'power_state': 'off',
            'blink_frequency': 0,
            'stop_indicator': 'off',
            'scroll_step': 1,
            'stop_indicator_blink_frequency': 0
        }
    ]
    
    # This stores various things related to whether a display needs to be refreshed and whether the configuration has changed
    UPDATE_DATA = [
        {
            'config_keys_changed': [],
            'config_specific': {},
            'message_changed': False,
            'sequence_cur_pos': None,
            'sequence_last_switched': None,
            'time_string_last_result': None
        },
        {
            'config_keys_changed': [],
            'config_specific': {},
            'message_changed': False,
            'sequence_cur_pos': None,
            'sequence_last_switched': None,
            'time_string_last_result': None
        },
        {
            'config_keys_changed': [],
            'config_specific': {},
            'message_changed': False,
            'sequence_cur_pos': None,
            'sequence_last_switched': None,
            'time_string_last_result': None
        },
        {
            'config_keys_changed': [],
            'config_specific': {},
            'message_changed': False,
            'sequence_cur_pos': None,
            'sequence_last_switched': None,
            'time_string_last_result': None
        }
    ]
    
    def __init__(self, controller, port = 1810, allowed_ip_match = None):
        self.running = False
        self.controller = controller
        self.port = port
        self.allowed_ip_match = allowed_ip_match
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.graphics = MatrixGraphics(controller)
        self.message_thread = threading.Thread(target = self.network_listen)
    
    def run(self):
        print("Starting server...")
        self.running = True
        self.message_thread.start()
        self.control_loop()
    
    def stop(self):
        print("Stopping server...")
        self.running = False
    
    def select_display(self, display):
        # Select a display using the multiplex chip
        if display == 0:
            self.controller.port.setDTR(0)
            self.controller.port.setRTS(0)
        elif display == 1:
            self.controller.port.setDTR(0)
            self.controller.port.setRTS(1)
        elif display == 2:
            self.controller.port.setDTR(1)
            self.controller.port.setRTS(0)
        elif display == 3:
            self.controller.port.setDTR(1)
            self.controller.port.setRTS(1)
    
    def network_listen(self):
        # Open the network socket and listen
        self.socket.bind(('', self.port))
        self.socket.settimeout(5.0)
        print("Listening on port %i" % self.port)
        self.socket.listen(1)
        
        try:
            while self.running:
                try:
                    # Wait for someone to connect
                    conn, addr = self.socket.accept()
                    ip, port = addr
                    if self.allowed_ip_match is not None and not ip.startswith(self.allowed_ip_match):
                        print("Discarding message from %s on port %i" % addr)
                        discard_message(conn)
                        continue
                    
                    print("Receiving message from %s on port %i" % addr)
                    # Receive the message
                    message = receive_message(conn)
                    if message is None:
                        # We received an invalid message, just discard it
                        continue
                    reply = self.process_message(message)
                    if reply:
                        send_message(conn, reply)
                except socket.timeout:
                    pass
                except KeyboardInterrupt:
                    raise
                except:
                    traceback.print_exc()
        except KeyboardInterrupt:
            self.stop()
        finally:
            self.socket.close()
    
    def control_loop(self):
        while self.running:
            try:
                for display, message in enumerate(self.CURRENT_MESSAGE):
                    now = time.time()
                    update_data = self.UPDATE_DATA[display]
                    
                    # Process configuration changes
                    for key in update_data['config_keys_changed']:
                        self.set_config(display, key, self.CURRENT_CONFIG[display][key])
                        if key == 'power_state' and self.CURRENT_CONFIG[display][key] == 'on':
                            update_data['message_changed'] = True
                    update_data['config_keys_changed'] = []
                    
                    if message is None or self.CURRENT_CONFIG[display]['power_state'] == 'off':
                        time.sleep(0.25)
                        continue
                    
                    if update_data['message_changed']:
                        if message['type'] == 'sequence':
                            update_data['sequence_cur_pos'] = 0
                            update_data['sequence_last_switched'] = now
                            update_data['time_string_last_result'] = None
                        elif message['type'] == 'text':
                            update_data['sequence_cur_pos'] = None
                            update_data['sequence_last_switched'] = None
                            if message['data'].get('parse_time_string', False):
                                update_data['time_string_last_result'] = datetime.datetime.now().strftime(message['data']['text'])
                            else:
                                update_data['time_string_last_result'] = None
                        elif message['type'] == 'bitmap':
                            update_data['sequence_cur_pos'] = None
                            update_data['sequence_last_switched'] = None
                            update_data['time_string_last_result'] = None
                    
                    if message['type'] == 'sequence':
                        actual_message = message['data'][update_data['sequence_cur_pos']]
                        sequence_needs_switching = now - update_data['sequence_last_switched'] >= actual_message['duration']
                    else:
                        actual_message = message
                        sequence_needs_switching = False
                    
                    if sequence_needs_switching:
                        if update_data['sequence_cur_pos'] == len(message['data']) - 1:
                            update_data['sequence_cur_pos'] = 0
                        else:
                            update_data['sequence_cur_pos'] += 1
                        actual_message = message['data'][update_data['sequence_cur_pos']]
                        update_data['sequence_last_switched'] = now
                    
                    if actual_message['type'] == 'text' and actual_message['data'].get('parse_time_string', False):
                        time_string_cur_result = datetime.datetime.now().strftime(actual_message['data']['text'])
                    
                    needs_refresh = update_data['message_changed'] or \
                                    actual_message['data'].get('parse_time_string', False) and \
                                    time_string_cur_result != update_data['time_string_last_result'] or \
                                    sequence_needs_switching
                    
                    if needs_refresh:
                        if actual_message['type'] == 'bitmap':
                            update_data['time_string_last_result'] = None
                            self.set_bitmap(display, 
                                            actual_message['data']['bitmap'],
                                            actual_message['data'].get('blend_bitmap', False),
                                            actual_message['data'].get('align'))
                        elif actual_message['type'] == 'text':
                            if actual_message['data'].get('parse_time_string', False):
                                update_data['time_string_last_result'] = time_string_cur_result
                                text = time_string_cur_result
                            else:
                                update_data['time_string_last_result'] = None
                                text = actual_message['data']['text']
                            
                            bitmap = self.graphics.build_text(text,
                                                              actual_message['data'].get('font', "Arial"),
                                                              actual_message['data'].get('size', 11),
                                                              actual_message['data'].get('align'))
                            
                            self.set_bitmap(display,
                                            bitmap,
                                            actual_message['data'].get('blend_bitmap', False))
                        
                        if sequence_needs_switching or update_data['message_changed']:
                            # Reset config items that haven't been specifically set to their global values
                            reset_keys = [key for key in update_data['config_specific'] if key not in actual_message.get('config', {})]
                            for key in reset_keys:
                                self.set_config(display, key, self.CURRENT_CONFIG[display][key])
                                update_data['config_specific'].pop(key, None)
                            
                            # Set message-specific config
                            for key, value in actual_message.get('config', {}).items():
                                if update_data['config_specific'].get(key) == value:
                                    continue
                                self.set_config(display, key, value)
                                update_data['config_specific'][key] = value
                    update_data['message_changed'] = False
                time.sleep(0.25)
            except KeyboardInterrupt:
                self.stop()
            except:
                traceback.print_exc()
    
    def process_message(self, message):
        success = True
        if message.get('type') not in ('control', 'data', 'query-config', 'query-message', 'query-bitmap'):
            return {'success': False, 'error': "'%s' is not a valid message type" % message.get('type')}
        
        if message['type'] == 'control':
            for display in message.get('displays', []):
                for key, value in message['message'].items():
                    if key in self.CURRENT_CONFIG[display]:
                        self.CURRENT_CONFIG[display][key] = value
                        self.UPDATE_DATA[display]['config_keys_changed'].append(key)
            return {'success': success}
        elif message['type'] == 'data':
            for display in message.get('displays', []):
                self.CURRENT_MESSAGE[display] = message['message']
                self.UPDATE_DATA[display]['message_changed'] = True
            return {'success': success}
        elif message['type'] == 'query-config':
            displays = message.get('displays')
            keys = message.get('keys')
            if displays is None:
                displays = (0, 1, 2, 3)
            
            reply = {}
            for display in displays:
                config = self.CURRENT_CONFIG[display]
                reply_config = {}
                for key, value in config.items():
                    if keys is None or key in keys:
                        reply_config[key] = value
                reply[display] = reply_config
            return reply
        elif message['type'] == 'query-message':
            displays = message.get('displays')
            if displays is None:
                displays = (0, 1, 2, 3)
            
            reply = dict(((display, self.CURRENT_MESSAGE[display]) for display in displays))
            return reply
        elif message['type'] == 'query-bitmap':
            displays = message.get('displays')
            if displays is None:
                displays = (0, 1, 2, 3)
            
            reply = dict(((display, self.CURRENT_BITMAP[display]) for display in displays))
            return reply
        
        # This should never be called
        return {'success': False}
    
    def set_bitmap(self, display, bitmap, blend_bitmap = False, align = None):
        print("set_bitmap", )
        new_bitmap = self.graphics.align_long_bitmap(bitmap, align)
        if blend_bitmap:
            resulting_bitmap = self.graphics.blend_long_bitmaps(self.CURRENT_BITMAP[display], new_bitmap)
        else:
            resulting_bitmap = new_bitmap
        self.CURRENT_BITMAP[display] = resulting_bitmap
        self.select_display(display)
        self.graphics.send_long_bitmap(resulting_bitmap)
        print("ok")
    
    def set_config(self, display, key, value):
        print("set_config", key, value, )
        try:
            func = getattr(self.controller, "set_%s" % key)
            self.select_display(display)
            func(value)
            print("ok")
        except:
            traceback.print_exc()
            return False
        return True



class MatrixClient(object):
    def __init__(self, host, port = 1810, timeout = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
    
    def send_raw_message(self, message, expect_reply = True):
        reply = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            send_message(sock, message)
            
            if expect_reply:
                reply = receive_message(sock)
        finally:
            sock.close()
        return reply
    
    def build_data_message(self, displays, message):
        return {'type': 'data', 'displays': displays, 'message': message}
    
    def build_control_message(self, displays, message):
        return {'type': 'control', 'displays': displays, 'message': message}
    
    def build_config_query_message(self, displays, keys):
        return {'type': 'query-config', 'displays': displays, 'keys': keys}
    
    def build_message_query_message(self, displays):
        return {'type': 'query-message', 'displays': displays}
    
    def build_bitmap_query_message(self, displays):
        return {'type': 'query-bitmap', 'displays': displays}
    
    def build_bitmap_message(self, bitmap, align = None, blend_bitmap = False, config = {}, duration = None):
        message = {'type': 'bitmap', 'config': config, 'data': {'align': align, 'blend_bitmap': blend_bitmap, 'bitmap': bitmap}}
        if duration:
            message['duration'] = duration
        return message
    
    def build_text_message(self, text, font = "Arial", size = 11, align = None, parse_time_string = False, blend_bitmap = False, config = {}, duration = None):
        message = {'type': 'text', 'config': config, 'data': {'align': align, 'font': font, 'size': size, 'parse_time_string': parse_time_string, 'blend_bitmap': blend_bitmap, 'text': text}}
        if duration:
            message['duration'] = duration
        return message
    
    def build_sequence_message(self, sequence, duration = None):
        # The duration parameter is used as the duration for messages in the sequence that don't have their own duration set.
        for message in sequence:
            if message['type'] == 'sequence':
                raise ValueError("Nesting of sequence messages is not allowed")
            if not message.get('duration'):
                if not duration:
                    raise ValueError("Sequence contains message with no specified duration, but no default duration was given")
                message['duration'] = duration
        return {'type': 'sequence', 'data': sequence}
    
    def send_data_message(self, displays, message):
        return self.send_raw_message(self.build_data_message(displays, message))
    
    def send_control_message(self, displays, message):
        return self.send_raw_message(self.build_control_message(displays, message))
    
    def send_config_query_message(self, displays, keys):
        return self.send_raw_message(self.build_config_query_message(displays, keys))
    
    def send_message_query_message(self, displays):
        return self.send_raw_message(self.build_message_query_message(displays))
    
    def send_bitmap_query_message(self, displays):
        return self.send_raw_message(self.build_bitmap_query_message(displays))
    
    def send_bitmap_message(self, displays, bitmap, align = None, blend_bitmap = False, config = {}):
        message = self.build_bitmap_message(bitmap, align, blend_bitmap, config)
        return self.send_data_message(displays, message)
    
    def send_text_message(self, displays, text, font = "Arial", size = 11, align = None, parse_time_string = False, blend_bitmap = False, config = {}):
        message = self.build_text_message(text, font, size, align, parse_time_string, blend_bitmap, config)
        return self.send_data_message(displays, message)
    
    def send_sequence_message(self, displays, sequence, duration = None):
        message = self.build_sequence_message(sequence, duration)
        return self.send_data_message(displays, message)
    
    def get_config(self, displays = None, keys = None):
        return self.send_config_query_message(displays, keys)
    
    def get_message(self, displays = None):
        return self.send_message_query_message(displays)
    
    def get_bitmap(self, displays = None):
        return self.send_bitmap_query_message(displays)
    
    def set_config(self, displays, config):
        return self.send_control_message(displays, config)
    
    def set_display_mode(self, displays, mode):
        return self.send_control_message(displays, {'display_mode': mode})
    
    def set_scroll_speed(self, displays, speed):
        return self.send_control_message(displays, {'scroll_speed': speed})
    
    def set_scroll_direction(self, displays, direction):
        return self.send_control_message(displays, {'scroll_direction': direction})
    
    def set_scroll_mode(self, displays, mode):
        return self.send_control_message(displays, {'scroll_mode': mode})
    
    def set_scroll_gap(self, displays, gap):
        return self.send_control_message(displays, {'scroll_gap': gap})
    
    def set_power_state(self, displays, state):
        return self.send_control_message(displays, {'power_state': state})
    
    def set_blink_frequency(self, displays, frequency):
        return self.send_control_message(displays, {'blink_frequency': frequency})
    
    def set_stop_indicator(self, displays, state):
        return self.send_control_message(displays, {'stop_indicator': state})
    
    def set_scroll_step(self, displays, step):
        return self.send_control_message(displays, {'scroll_step': step})
    
    def set_stop_indicator_blink_frequency(self, displays, frequency):
        return self.send_control_message(displays, {'stop_indicator_blink_frequency': frequency})