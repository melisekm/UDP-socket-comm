import struct
import socket
from uzol import Uzol
from utils import CheckSumError


class Server(Uzol):
    def __init__(self, crc, constants, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.bind(("192.168.100.20", port))
        self.sock.settimeout(60)
        self.crc = crc
        self.constants = constants
        self.buffer = 1500
        self.adresa = None

    def get_type(self, vstup):
        res = []
        for typ in self.constants.types.items():
            if vstup & typ[0]:
                res.append(typ[1])
        return res

    def recv_simple(self, typ):
        data, addr = self.sock.recvfrom(self.buffer)
        unpacked = struct.unpack("=cH", data[:3])
        if not self.crc.check_crc(unpacked):
            raise CheckSumError
        types = self.get_type(unpacked[0])
        if typ in types:
            return True
        return False

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN")

            # self.sock.settimeout(60)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
        except socket.timeout:
            print("Cas vyprsal")

    def listen(self):
        self.nadviaz_spojenie
