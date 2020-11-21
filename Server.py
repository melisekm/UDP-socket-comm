import struct
import socket
from uzol import Uzol
from utils import CheckSumError


class Server(Uzol):
    def __init__(self, crc, constants, port):
        super().__init__(crc, constants)
        self.sock.bind(("localhost", port))
        self.crc = crc
        self.constants = constants
        self.buffer = 1500

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.buffer)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.buffer)
            # self.sock.settimeout(60)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
        except socket.timeout:
            print("Cas vyprsal")

    def listen(self):
        self.nadviaz_spojenie()
