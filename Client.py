import os
import socket
import struct
import math
from uzol import Uzol
from utils import CheckSumError


class Client(Uzol):
    def __init__(self, crc, constants, adresa, max_fragment_size, odosielane_data, chyba):
        super().__init__(crc, constants)
        self.target = adresa
        self.send_buffer = max_fragment_size
        self.constants.CHYBA = chyba
        self.odosielane_data = {
            "TYP": "DF" if odosielane_data[0] == "subor" else "DM",
            "DATA": odosielane_data[1],
        }
        if self.odosielane_data["TYP"] == "DF":
            file_size = os.stat(self.odosielane_data["DATA"]).st_size
            self.pocet_fragmentov = math.ceil(file_size / self.send_buffer)
        else:
            self.pocet_fragmentov = math.ceil(len(self.odosielane_data["DATA"]) / self.send_buffer)

    def send_info(self, typ):
        if "DF" in typ:
            data = self.odosielane_data["DATA"]
        else:
            data = None
        typ = ("INIT", typ)
        print(f"POSLAL:{typ}")
        self.send_data(typ, self.pocet_fragmentov, "=cI", data, self.constants.BEZ_CHYBY)

        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            print("Poskodeny packet, chyba pri init sprave ACK")
            raise
        except socket.timeout:
            print("Cas vyprsal pri info pkt ACK")
            raise

    def get_corrupted_ids(self, unpacked_ids):
        res = [None] * self.velkost_bloku
        size = 0
        for bit in range(self.velkost_bloku):
            if unpacked_ids & (1 << bit):
                size += 1
                res[bit] = 1
        return res, size

    def recv_data_confirmation(self, block_data):
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
            unpacked_ids = struct.unpack("=i", data[1:5])[0]
            corrupted_ids, bad_count = self.get_corrupted_ids(unpacked_ids)
            print(
                f"ID CORUPTED PACKETOV: {[i+1 for i,x in enumerate(corrupted_ids) if x is not None]}, pocet:{bad_count}"
            )
            ids = [idx for idx, x in enumerate(corrupted_ids) if x is not None]
            sent_good = 0
            while sent_good != bad_count:
                print(f"Opatovne posielam block_id:{ids[sent_good]+1}/{self.velkost_bloku}.")
                self.send_data(
                    (self.odosielane_data["TYP"]),
                    bytes([ids[sent_good]]),
                    "=cc",
                    block_data[ids[sent_good]],
                    self.constants.BEZ_CHYBY,
                )
                sent_good += 1
            try:
                self.send_simple("ACK", self.target)
                self.recv_simple("ACK", self.recv_buffer)
            except CheckSumError:
                print("CHKSUM ERROR pri potvrdeni o znovuodoslati dat.")
                raise
            except socket.timeout:
                print("Nedostal potvrdenie pri znovuodoslani dat.")
                raise

    def load_block(self, obj_to_send, size, total_cntr):
        res = []
        if self.odosielane_data["TYP"] == "DF":
            while len(res) != size:
                res.append(obj_to_send.read(self.send_buffer))
        else:
            for i in range(size):
                start = total_cntr * self.send_buffer + i * self.send_buffer
                end = start + self.send_buffer
                res.append(obj_to_send[start:end])
        return res

    def open_obj_to_send(self):
        if self.odosielane_data["TYP"] == "DF":
            return open(self.odosielane_data["DATA"], "rb")
        return self.odosielane_data["DATA"]

    def send(self):
        self.send_info(self.odosielane_data["TYP"])
        obj_to_send = self.open_obj_to_send()
        total_cntr = 0
        block_id = 0
        block_data = self.load_block(obj_to_send, self.velkost_bloku, total_cntr)
        while True:
            # raw_data = file.read(self.send_buffer)
            if block_id >= self.velkost_bloku or total_cntr >= self.pocet_fragmentov:
                self.recv_data_confirmation(block_data)
                block_id = 0
                block_data = self.load_block(obj_to_send, self.velkost_bloku, total_cntr)
                if total_cntr == self.pocet_fragmentov:
                    break

            raw_data = block_data[block_id]

            # self.send_data(self.odosielane_data["TYP"], bytes([block_id]), "=cc", raw_data, self.constants.BEZ_CHYBY)

            # if (total_cntr + 1) % 4 == 0:
            #    print(f"Posielam block_id:{block_id+1}/{self.velkost_bloku}.")
            #    self.send_data(self.odosielane_data["TYP"], bytes([block_id]), "=cc", raw_data, 100)
            #    self.x5.append(total_cntr % self.velkost_bloku)
            # else:
            # if total_cntr == 0:
            #    for _ in range(5):
            #        print(f"Posielam block_id:{block_id+1}/{self.velkost_bloku}.")
            #        self.send_data(self.odosielane_data["TYP"], bytes([block_id]), "=cc", raw_data, 100)

            # else:
            print(f"Posielam block_id:{block_id+1}/{self.velkost_bloku}.")
            self.send_data(
                (self.odosielane_data["TYP"]),
                bytes([block_id]),
                "=cc",
                raw_data,
                100,
            )

            block_id += 1
            total_cntr += 1
            print(f"Celkovo je to {total_cntr}/{self.pocet_fragmentov}")

        print("Subor uspesne odoslany.")
        if self.odosielane_data["TYP"] == "DF":
            obj_to_send.close()

    def nadviaz_spojenie(self):
        try:
            self.send_simple("SYN", self.target)
            self.recv_simple(("SYN", "ACK"), self.recv_buffer)
            self.send_simple("ACK", self.target)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
            raise
        except socket.timeout:
            print("Cas vyprsal pri inicializacii")
            raise
        print("Spojenie nadviazane\n")

    def init(self):
        self.sock.settimeout(60)
        # spusti KA.
        try:
            self.nadviaz_spojenie()
            while True:
                self.send()  # main loop :D
                vstup = input("[Rovnaky] target/[quit]")  # spusti timer?
                if vstup.lower() == "quit":
                    self.send_simple("FIN", self.target)
                    self.recv_simple("ACK", self.recv_buffer)  # je mozne riesit dalej
                    break
                if vstup.lower() == "rovnaky":
                    # spusti KA
                    # zadajte odosielane data: pokial je vtomto menu posielaj KA
                    input()
                else:
                    break
        except CheckSumError as e:
            print(e.msg)
            print("CHKSUM ERROR pri odosielani dat.")
        except socket.timeout:
            print("Cas vyprsal pri odosielani dat.")

        self.sock.close()
