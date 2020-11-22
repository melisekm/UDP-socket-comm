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

    def send_data(self, typ, hdr_info, hdr_size, raw_data):
        header = []
        header.append(self.vytvor_type(typ))
        header.append(hdr_info)
        packed_hdr = struct.pack(hdr_size, header[0], header[1])
        data = packed_hdr + raw_data.encode()
        chksum = struct.pack("=H", self.crc.calculate(data))
        data_packed = data + chksum
        self.sock.sendto(data_packed, self.target)

    def send_info(self, typ):
        # self.send_fragment(typ,self.pocet_fragmentov,data )
        typ = ("INIT", typ)
        if typ == "DF":
            data = self.odosielane_data["DATA"].encode()
        else:
            data = ""
        self.send_data(typ, self.pocet_fragmentov, "=ci", data)

        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            # TODO RIES
            print("Poskodeny packet, chyba pri init sprave ACK")
        except socket.timeout:
            print("Cas vyprsal pri info pkt ACK")

    def recv_data_confirmation(self, block_data):
        pass

    def send_subor(self):
        self.send_info("DF")
        file = open(self.odosielane_data["DATA"])
        raw_data = file.read(self.send_buffer)
        total_cntr = 1
        block_cntr = 0
        block_data = []
        while raw_data:
            if block_cntr == 10:
                self.recv_data_confirmation(block_data)
            self.send_data("DF", block_cntr, "=cH", raw_data)
            block_data.append(raw_data)
            raw_data = file.read(self.send_buffer)
            block_cntr += 1
            total_cntr += 1

        file.close()

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
