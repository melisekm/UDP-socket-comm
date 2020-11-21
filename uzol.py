import struct
import socket


class Uzol:
    def __init__(self, crc, constants):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.crc = crc
        self.constants = constants