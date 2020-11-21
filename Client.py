import os
import socket
import struct
import math


class Client:
    def __init__(self, crc, constants, adresa, max_fragment_size, odosielane_data):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.crc = crc
        self.constants = constants
        self.target = {
            "IP": adresa[0],
            "PORT": adresa[1],
        }
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

    def nadviaz_spojenie(self):
        pass

    def send(self):
        self.nadviaz_spojenie()
        if self.odosielane_data["TYP"] == "subor":
            self.send_subor()
        else:
            self.send_sprava()