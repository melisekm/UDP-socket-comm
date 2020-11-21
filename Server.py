import struct
import socket


class Server:
    def __init__(self, crc, constants, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.bind(("192.168.100.20", port))
        self.crc = crc
        self.constants = constants
        self.buffer = 1500

    def listen(self):
        pass
