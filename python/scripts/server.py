#!/usr/bin/env python3

import argparse
from annax import MatrixController, MatrixServer

def main():
    parser = argparse.ArgumentParser(description = "Command-line control script for a matrix controller")
    parser.add_argument('-sp', '--serial-port', type = str, required = True,
        help = "The serial port to use for communication with the matrix controller")
    parser.add_argument('-b', '--baudrate', type = int, default = 115200,
        help = "The baudrate to use for communication with the matrix controller (Default: 115200)")
    parser.add_argument('-p', '--port', type = int, default = 1810,
        help = "The port for the server to listen on (Default: 1810)")
    parser.add_argument('-d', '--debug', action = 'store_true',
        help = "Enable debug output")
    parser.add_argument('-cd', '--controller-debug', action = 'store_true',
        help = "Enable debug output of serial communication")
    parser.add_argument('-ip', '--allowed-ips', type = str,
        help = "A string that each ip that wants to connect has to begin with")
    
    args = parser.parse_args()
    controller = MatrixController(args.serial_port, baudrate = args.baudrate, debug = args.controller_debug)
    server = MatrixServer(controller, port = args.port, allowed_ip_match = args.allowed_ips, debug = args.debug)
    server.run()

if __name__ == "__main__":
    main()