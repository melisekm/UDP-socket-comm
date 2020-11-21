import struct
import socket
import time
from uzol import Uzol
from utils import CheckSumError


class Server(Uzol):
    def __init__(self, crc, constants, port):
        super().__init__(crc, constants)
        self.sock.bind(("192.168.100.10", port))
        self.crc = crc
        self.constants = constants
        self.buffer = 1500

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.buffer)
            self.sock.settimeout(2)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.buffer)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
        except socket.timeout:
            print("Cas vyprsal")

    def listen(self):
        self.nadviaz_spojenie()
