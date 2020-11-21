import os
import socket
import struct
import math
from uzol import Uzol


class Client(Uzol):
    def __init__(self, crc, constants, adresa, max_fragment_size, odosielane_data):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.crc = crc
        self.constants = constants
        self.target = adresa
        self.buffer = max_fragment_size
        self.odosielane_data = {
            "TYP": odosielane_data[0],
            "DATA": odosielane_data[1],
        }
        if self.odosielane_data["TYP"] == "subor":
            self.file_size = os.stat(self.odosielane_data["DATA"]).st_size
            self.pocet_fragmentov = math.ceil(self.file_size / self.buffer)
        else:
            self.pocet_fragmentov = math.ceil(len(self.odosielane_data["DATA"] / self.buffer))

    def send_subor(self):
        pass

    def send_sprava(self):
        pass

    def vytvor_type(self, vstup):
        result = 0
        for typ in vstup:
            result |= self.constants.types[typ]
        return result

    def send_simple(self, typ):
        hdr = self.vytvor_type(typ)
        chksum = self.crc(hdr)
        packed = struct.pack("=cH", hdr, chksum)
        data = packed
        self.sock.sendto(data, self.target)

    def nadviaz_spojenie(self):
        self.send_simple("SYN")

    def send(self):
        self.nadviaz_spojenie()
        if self.odosielane_data["TYP"] == "subor":
            self.send_subor()
        else:
            self.send_sprava()
