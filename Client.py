import os
import socket
import struct
import math
import time
from uzol import Uzol
from utils import CheckSumError


class Client(Uzol):
    def __init__(self, crc, constants, adresa, max_fragment_size, odosielane_data, chyba):
        super().__init__(crc, constants)
        self.target = adresa
        self.send_buffer = max_fragment_size
        self.recv_buffer = 1500
        self.constants.CHYBA = chyba
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
        if "DF" in typ:
            data = self.odosielane_data["DATA"]
        else:
            data = None
        typ = ("INIT", typ)
        print("POSLAL:INIT")
        self.send_data(typ, self.pocet_fragmentov, "=ci", data, self.constants.BEZ_CHYBY)

        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            # TODO RIES
            print("Poskodeny packet, chyba pri init sprave ACK")
        except socket.timeout:
            print("Cas vyprsal pri info pkt ACK")

    def get_corrupted_ids(self, unpacked_ids):
        res = [None] * self.posielane_size
        size = 0
        for bit in range(self.posielane_size):
            if unpacked_ids & (1 << bit):
                size += 1
                res[bit] = 1
        return res, size

    def recv_data_confirmation(self, block_data, total_cntr):
        data = self.sock.recvfrom(self.recv_buffer)[0]
        sender_chksum = struct.unpack("=H", data[-2:])[0]
        if not self.crc.check(data[:-2], sender_chksum):
            raise CheckSumError("ChcekSum error pri ACK/NACK.")
            # TODO Doriesit
        unpacked_typ = struct.unpack("=c", data[:1])[0]
        types = self.get_type(unpacked_typ)
        if "ACK" in types:
            print("Block potvrdeny.")
            return
        if "NACK" in types:
            unpacked_ids = struct.unpack("=H", data[1:3])[0]
            corrupted_ids, bad_count = self.get_corrupted_ids(unpacked_ids)
            print(f"ID CORUPTED PACKETOV: {corrupted_ids}, pocet:{bad_count}")
            total_cntr -= bad_count
            ids = [i for i, x in enumerate(corrupted_ids) if x is not None]
            print(f"ids:{ids}")
            sent_good = 0
            while sent_good != bad_count:
                print(f"Opatovne Posielam block_id:{ids[sent_good]}/{self.posielane_size}.")
                self.send_data(
                    "DF", ids[sent_good], "=cH", block_data[ids[sent_good]], self.constants.BEZ_CHYBY
                )
                sent_good += 1
                total_cntr += 1
                # time.sleep(0.5)
            try:
                self.recv_simple("ACK", self.recv_buffer)
            except CheckSumError:
                print("CHKSUM ERROR pri potvrdeni o znovuodoslati dat.")
            except socket.timeout:
                print("Nedostal potvrdenie pri znovuodoslani dat.")

    def send_subor(self):
        self.send_info("DF")
        file = open(self.odosielane_data["DATA"], "rb")
        raw_data = file.read(self.send_buffer)
        total_cntr = 0
        block_id = 0
        block_data = []
        while True:
            if block_id == 10 or total_cntr == self.pocet_fragmentov:
                self.recv_data_confirmation(block_data, total_cntr)
                block_id = 0
                block_data = []
                if total_cntr == self.pocet_fragmentov:
                    break
            print(f"Posielam block_id:{block_id+1}/{self.posielane_size}.")
            self.send_data("DF", block_id, "=cH", raw_data, self.constants.CHYBA)

            block_data.append(raw_data)
            raw_data = file.read(self.send_buffer)
            block_id += 1
            total_cntr += 1
            print(f"Celkovo je to {total_cntr}/{self.pocet_fragmentov}")
        # tu bude nameisto tohto este FIN
        print("Subor uspesne odoslany.")
        time.sleep(5)
        file.close()

    def send_sprava(self):
        self.send_info("DM")
        pass

    def nadviaz_spojenie(self):
        try:
            self.send_simple("SYN", self.target)
            self.recv_simple(("SYN", "ACK"), self.recv_buffer)
            self.send_simple("ACK", self.target)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
        except socket.timeout:
            print("Cas vyprsal pri inicializacii")

    def send(self):
        self.sock.settimeout(60)
        self.nadviaz_spojenie()
        try:
            if self.odosielane_data["TYP"] == "subor":
                self.send_subor()
            else:
                self.send_sprava()
        except CheckSumError as e:
            print(e.msg)
            print("CHKSUM ERROR pri odosielani dat.")
        except socket.timeout:
            print("Cas vyprsal pri odosielani dat.")
        self.sock.close()
