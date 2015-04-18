#!/usr/bin/env python3

import argparse
from matrix_controller import MatrixController
from matrix_server import MatrixServer

def main():
    parser = argparse.ArgumentParser(description = "Command-line control script for a matrix controller")
    parser.add_argument('-p', '--port', type = str, default = "/dev/ttyACM0",
        help = "The serial port to use for communication with the matrix controller (Default: /dev/ttyACM0)")
    parser.add_argument('-b', '--baudrate', type = int, default = 57600,
        help = "The baudrate to use for communication with the matrix controller (Default: 57600)")
    
    args = parser.parse_args()
    controller = MatrixController(args.port, baudrate = args.baudrate)
    server = MatrixServer(controller)
    server.run()