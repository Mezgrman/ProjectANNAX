#!/usr/bin/env python3

import argparse
from matrix_controller import MatrixController
from matrix_server import MatrixServer

def main():
    parser = argparse.ArgumentParser(description = "Command-line control script for a matrix controller")
    parser.add_argument('-sp', '--serial-port', type = str, required = True,
        help = "The serial port to use for communication with the matrix controller")
    parser.add_argument('-b', '--baudrate', type = int, default = 57600,
        help = "The baudrate to use for communication with the matrix controller (Default: 57600)")
    parser.add_argument('-p', '--port', type = int, default = 1810,
        help = "The port for the server to listen on (Default: 1810)")
    parser.add_argument('-d', '--debug', action = 'store_true',
        help = "Enable debug output")
    parser.add_argument('-ip', '--allowed-ips', type = str,
        help = "A string that each ip that wants to connect has to begin with")
    
    args = parser.parse_args()
    controller = MatrixController(args.serial_port, baudrate = args.baudrate, debug = args.debug)
    server = MatrixServer(controller, port = args.port, allowed_ip_match = args.allowed_ips)
    server.run()

if __name__ == "__main__":
    main()