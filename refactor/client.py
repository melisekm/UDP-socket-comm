import os
import socket
import struct
import math
import time
from concurrent.futures import ThreadPoolExecutor
from utils import CheckSumError, get_input
from uzol import Uzol


class Client(Uzol):
    def __init__(self, crc, constants, adresa, max_fragment_size, odosielane_data, chyba):
        super().__init__(crc, constants)
        self.target = adresa
        self.ka = False
        self.constants.CHYBA = chyba
        self.parse_args(max_fragment_size, odosielane_data)

    def parse_args(self, max_fragment_size, odosielane_data):
        self.send_buffer = max_fragment_size
        self.odosielane_data = {
            "TYP": "DF" if odosielane_data[0] == "subor" else "DM",
            "DATA": odosielane_data[1],
        }
        if self.odosielane_data["TYP"] == "DF":
            file_size = os.stat(self.odosielane_data["DATA"]).st_size
            self.pocet_fragmentov_data = math.ceil(file_size / self.send_buffer)
            dlzka_meno = len(os.path.basename(self.odosielane_data["DATA"]))
            self.pocet_fragmentov_nazov = math.ceil(dlzka_meno / self.send_buffer)
        else:
            self.pocet_fragmentov_data = math.ceil(len(self.odosielane_data["DATA"]) / self.send_buffer)

    def send_corrupted(self, block_data, data):
        bad_count = struct.unpack("=I", data[0:4])[0]
        corrupted_ids = list(map(int, data[4:].decode().split(",")))
        # data[4:] je bytes, decode na string, split na list, a convert vsetky na int cez list(map(int,string))
        print(f"ID corrupted packetov:{[x+1 for x in corrupted_ids]}, pocet:{bad_count}")
        for i in range(bad_count):
            print(f"Opatovne posielam block_id:{corrupted_ids[i]+1}/{self.velkost_bloku}.")
            self.send_data(
                self.typ,
                corrupted_ids[i],
                "=cI",
                block_data[corrupted_ids[i] % self.velkost_bloku],
                self.constants.BEZ_CHYBY,
            )
        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            print("CHKSUM ERROR pri potvrdeni o znovuodoslati dat.")
            raise
        except socket.timeout:
            print("Nedostal potvrdenie pri znovuodoslani dat.")
            raise

    def recv_data_confirmation(self, block_data):
        recvd_data = self.recvfrom(self.recv_buffer)
        if recvd_data is None:
            raise CheckSumError("ChcekSum error pri ACK/NACK.")
        unpacked_typ = struct.unpack("=c", recvd_data[:1])[0]
        types = self.get_type(unpacked_typ, recvd_data)
        if "ACK" in types:
            print("Block potvrdeny.")
        elif "NACK" in types:
            self.send_corrupted(block_data, recvd_data[1:-2])

    def open_obj_to_send(self):
        if self.typ == "DF":
            return open(self.odosielane_data["DATA"], "rb")
        return self.odosielane_data["DATA"]

    def load_block(self, obj, total_cntr):
        res = []
        if self.typ == "DF":
            while len(res) != self.velkost_bloku:
                res.append(obj.read(self.send_buffer))
        else:
            for i in range(self.velkost_bloku):
                start = total_cntr * self.send_buffer + i * self.send_buffer
                end = start + self.send_buffer
                res.append(obj[start:end])
        return res

    def send_fragments(self, typ, pocet_fragmentov):
        self.typ = typ
        obj_to_send = self.open_obj_to_send()
        total_cntr = 0
        block_id = 0
        block_data = self.load_block(obj_to_send, total_cntr)
        while True:
            if block_id >= self.velkost_bloku or total_cntr >= pocet_fragmentov:
                self.recv_data_confirmation(block_data)
                block_id = 0
                block_data = self.load_block(obj_to_send, total_cntr)
                if total_cntr == pocet_fragmentov:
                    break

            raw_data = block_data[block_id]
            print(f"Posielam block_id:{block_id+1}/{self.velkost_bloku}.")
            self.send_data(
                self.typ,
                total_cntr,
                "=cI",
                raw_data,
                self.constants.CHYBA,
            )
            block_id += 1
            total_cntr += 1
            print(f"Celkovo je to {total_cntr}/{pocet_fragmentov}")

        print("Data uspesne odoslane.")
        if self.typ == "DF":
            obj_to_send.close()

    def send_info(self, typ, pocet):
        self.send_data(typ, pocet, "=cI", None, self.constants.BEZ_CHYBY)
        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            print("Poskodeny packet, chyba pri init sprave ACK")
            raise
        except socket.timeout:
            print("Cas vyprsal pri info pkt ACK")
            raise

    def send_data_init(self):
        if self.odosielane_data["TYP"] == "DF":
            self.send_info(("INIT", "DF"), self.pocet_fragmentov_nazov)
            self.send_fragments("DM", self.pocet_fragmentov_nazov)
            self.send_info(("INIT", "DF"), self.pocet_fragmentov_data)
            self.send_fragments("DF", self.pocet_fragmentov_data)
        elif self.odosielane_data["TYP"] == "DM":
            self.send_info(("INIT", "DM"), self.pocet_fragmentov_data)
            self.send_fragments("DM", self.pocet_fragmentov_data)

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

    def send_fin(self):
        print("Ukoncujem spojenie..")
        self.send_simple("FIN", self.target)
        self.recv_simple("ACK", self.recv_buffer)  # je mozne riesit dalej

    def send_ka(self):
        print("SPUSTAM KEEP ALIVE KAZDYCH 10 SEC")
        self.sock.settimeout(1)
        self.ka = True
        start = time.time()
        while True:
            try:
                if self.ka and time.time() - start > 10:
                    self.send_simple("KA", self.target)
                    self.recv_simple("ACK", self.recv_buffer)
                    start = time.time()
                elif self.ka is False:
                    print("VYPINAM KEEP ALIVE")
                    return 0
            # time.sleep(10)
            except (socket.timeout, ConnectionResetError):
                if self.ka is False:
                    return 0
                print("Nedostal potvrdenie na KA. Posielam opatovne.")
                self.sock.settimeout(1)
                try:
                    self.send_simple("KA", self.target)
                    self.recv_simple("ACK", self.recv_buffer)
                    start = time.time()
                except (socket.timeout, ConnectionResetError):
                    print("Cas uplynul vypinam keep alive a ukoncujem spojenie.")
                    self.ka = False
                    return 1

    def get_vstup(self):
        while True:
            vstup = input("[Rovnaky] target/[quit]:\n")  # spusti timer?
            if vstup.lower() == "quit":
                if self.ka is False:
                    print("Cas vyprsal.")
                    return 0
                self.send_fin()
                self.ka = False
                return 0
            if vstup.lower() == "rovnaky":
                max_fragment_size, odosielane_data = get_input(self.ka)
                if self.ka is False:
                    print("Cas vyprsal.")
                    return 0
                self.ka = False
                self.parse_args(max_fragment_size, odosielane_data)
                return 1
            print("neplatny vstup")

    def enable_ka_get_input(self):
        with ThreadPoolExecutor() as executor:
            send_ka = executor.submit(self.send_ka)
            vstup = executor.submit(self.get_vstup)
            if send_ka.result() == 1:
                print("konec ka")
                return 0
            if vstup.result() == 0:
                print("odpalujem loop")
                return 0
            if vstup.result() == 1:
                print("zadali ste rovnaky")
                return 1
        print("drumroll")

    def run(self):
        self.sock.settimeout(5)
        try:
            self.nadviaz_spojenie()
            while True:
                self.send_data_init()  # main loop
                if self.enable_ka_get_input() == 0:
                    break
        except CheckSumError as e:
            print(e.msg)
            print("CHKSUM ERROR pri odosielani dat.")
        except socket.timeout:
            print("Cas vyprsal pri odosielani dat.")
        self.sock.close()
