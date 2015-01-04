#!/usr/bin/env python3

from matrix_controller import MatrixController
from matrix_server import MatrixServer

controller = MatrixController("/dev/ttyUSB0")
server = MatrixServer(controller)
server.run()