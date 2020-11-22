import os
import socket
import struct
import math
import time
from uzol import Uzol
from utils import CheckSumError


class Client(Uzol):
    def __init__(self, crc, constants, adresa, max_fragment_size, odosielane_data):
        super().__init__(crc, constants)
        self.target = adresa
        self.send_buffer = max_fragment_size
        self.recv_buffer = 1500
        self.odosielane_data = {
            "TYP": odosielane_data[0],
            "DATA": odosielane_data[1],
        }
        if self.odosielane_data["TYP"] == "subor":
            self.file_size = os.stat(self.odosielane_data["DATA"]).st_size
            self.pocet_fragmentov = math.ceil(self.file_size / self.send_buffer)
        else:
            self.pocet_fragmentov = math.ceil(len(self.odosielane_data["DATA"] / self.send_buffer))

    def send_info(self, typ):
        header = []
        header.append(self.vytvor_type(("INIT", typ)))
        header.append(self.pocet_fragmentov)
        packed_hdr = struct.pack("=ci", header[0], header[1])
        data = packed_hdr
        if typ == "DF":
            data += self.odosielane_data["DATA"].encode()
        chksum = struct.pack("=H", self.crc.calculate(data))
        data_packed = data + chksum
        self.sock.sendto(data_packed, self.target)
        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            # TODO RIES
            print("Poskodeny packet, chyba pri init sprave ACK")
        except socket.timeout:
            print("Cas vyprsal pri info pkt ACK")

    def send_subor(self):
        self.send_info("DF")
        pass

    def send_sprava(self):
        self.send_info("DM")
        pass

    def nadviaz_spojenie(self):
        self.sock.settimeout(2)
        try:
            self.send_simple("SYN", self.target)
            self.recv_simple(("SYN", "ACK"), self.recv_buffer)
            self.send_simple("ACK", self.target)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
        except socket.timeout:
            print("Cas vyprsal pri inicializacii")

    def send(self):
        self.nadviaz_spojenie()
        if self.odosielane_data["TYP"] == "subor":
            self.send_subor()
        else:
            self.send_sprava()
        self.sock.close()
