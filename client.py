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
        self.KA_cycle = 10
        self.parse_args(max_fragment_size, odosielane_data, chyba)

    def parse_args(self, max_fragment_size, odosielane_data, chyba):
        self.constants.CHYBA = chyba
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

    def send_corrupted(self, block_data, data, pocet_fragmentov):
        bad_count = struct.unpack("=I", data[0:4])[0]
        corrupted_ids = list(map(int, data[4:].decode().split(",")))
        # data[4:] je bytes, decode na string, split na list, a convert vsetky na int cez list(map(int,string))
        self.logger.log(f"\nID corrupted packetov:{[x+1 for x in corrupted_ids]}\n", 1)
        for i in range(bad_count):
            print(f"Opatovne posielam block_id:{corrupted_ids[i]+1}/{pocet_fragmentov}.")
            self.send_data(
                self.typ,
                corrupted_ids[i],
                "=cI",
                block_data[corrupted_ids[i] % self.velkost_bloku],
                self.constants.BEZ_CHYBY,
            )
        try:
            self.recv_data_confirmation(block_data, pocet_fragmentov)
        except CheckSumError:
            self.logger.log("CHKSUM ERROR pri potvrdeni o znovuodoslati dat.", 1)
            raise
        except socket.timeout:
            self.logger.log("Nedostal potvrdenie pri znovuodoslani dat.", 1)
            raise

    def recv_data_confirmation(self, block_data, pocet_fragmentov):
        recvd_data = self.recvfrom()
        if recvd_data is None:
            raise CheckSumError("ChcekSum error pri ACK/NACK.")
        unpacked_typ = struct.unpack("=c", recvd_data[:1])[0]
        types = self.get_type(unpacked_typ, recvd_data)
        if "ACK" in types:
            self.logger.log("Block potvrdeny.\n", 1)
        elif "NACK" in types:
            self.send_corrupted(block_data, recvd_data[1:-2], pocet_fragmentov)

    def open_obj_to_send(self):
        if self.typ == "DF":
            return open(self.odosielane_data["DATA"], "rb")
        return self.odosielane_data["DATA"]

    def close_obj(self, obj):
        self.logger.log("Data uspesne odoslane.", 1)
        if self.typ == "DF":
            obj.close()

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
        if pocet_fragmentov == 0:
            self.close_obj(obj_to_send)
            return
        while True:
            if block_id >= self.velkost_bloku or total_cntr >= pocet_fragmentov:
                self.recv_data_confirmation(block_data, pocet_fragmentov)
                block_id = 0
                block_data = self.load_block(obj_to_send, total_cntr)
                if total_cntr >= pocet_fragmentov:
                    break
            print(f"Posielam block_id:{block_id+1}/{self.velkost_bloku}.")
            raw_data = block_data[block_id]

            if self.constants.CHYBA < 0 and (total_cntr + 1) == -self.constants.CHYBA:
                self.send_data(
                    self.typ,
                    total_cntr,
                    "=cI",
                    raw_data,
                    100,
                )
            else:
                self.send_data(
                    self.typ,
                    total_cntr,
                    "=cI",
                    raw_data,
                    self.constants.CHYBA,
                )

            block_id += 1
            total_cntr += 1
            print(f"Celkovo je to {total_cntr}/{pocet_fragmentov}\n")

        self.close_obj(obj_to_send)

    def send_info(self, typ, pocet):
        self.send_data(typ, pocet, "=cI", None, self.constants.BEZ_CHYBY)
        try:
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError:
            self.logger.log("Poskodeny packet, chyba pri init sprave ACK", 5)
            raise
        except socket.timeout:
            self.logger.log("Cas vyprsal pri info pkt ACK", 5)
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
            self.logger.log("Poskodeny packet, chyba pri nadviazani spojenia", 5)
            raise
        except socket.timeout:
            self.logger.log("Cas vyprsal pri inicializacii", 5)
            raise
        self.logger.log("Spojenie nadviazane.\n", 1)

    def send_fin(self):
        print("Vypinam KeepAlive a ukoncujem spojenie..")
        self.send_simple("FIN", self.target)
        self.recv_simple("ACK", self.recv_buffer)

    def send_ka(self):
        self.logger.log("SPUSTAM KEEP ALIVE KAZDYCH 10 SEC", 1)
        self.sock.settimeout(2)
        self.ka = True
        while True:
            try:
                if self.ka:
                    self.send_simple("KA", self.target)
                    self.recv_simple("ACK", self.recv_buffer)
                elif self.ka is False:
                    self.logger.log("VYPINAM KEEP ALIVE", 1)
                    return 0
            except (socket.timeout, ConnectionResetError):
                if self.ka is False:
                    return 0
                print("\nNedostal potvrdenie na KA. Posielam opatovne.")
                self.sock.settimeout(2)
                try:
                    self.send_simple("KA", self.target)
                    self.recv_simple("ACK", self.recv_buffer)
                except (socket.timeout, ConnectionResetError):
                    print("\nNeodstal ani opatovne potvrdenie. Vypinam keep alive a ukoncujem spojenie.")
                    self.ka = False
                    return 1
            time.sleep(self.KA_cycle)

    def get_vstup(self):
        while True:
            vstup = input("[Rovnaky] target / [toggle] KA spam: / [fin] ukonci spojenie\n")
            if vstup.lower() == "fin":
                if self.ka is False:
                    print("Spojenie bolo ukoncene.")
                    return 0
                self.send_fin()
                self.ka = False
                return 0
            if vstup.lower() == "rovnaky":
                max_fragment_size, odosielane_data, chyba = get_input(self.ka)
                if self.ka is False or max_fragment_size is None:
                    print("Spojenie bolo ukoncene.")
                    self.ka = False
                    return 0
                self.ka = False
                self.parse_args(max_fragment_size, odosielane_data, chyba)
                print("Vypinam KeepAlive...")
                return 1
            if vstup.lower() == "toggle":
                self.logger.print = not self.logger.print
            else:
                print("neplatny vstup")

    def enable_ka_get_input(self):
        with ThreadPoolExecutor() as executor:
            send_ka = executor.submit(self.send_ka)
            vstup = executor.submit(self.get_vstup)
            if send_ka.result() == 1:
                return 0
            if vstup.result() == 0:
                return 0
            if vstup.result() == 1:
                return 1

    def run(self):
        self.sock.settimeout(3)
        try:
            self.nadviaz_spojenie()
            while True:
                self.send_data_init()  # main loop
                if self.enable_ka_get_input() == 0:
                    break
                self.logger.print = True
        except CheckSumError as e:
            self.logger.log(e.msg, 5)
            self.logger.log("CHKSUM ERROR pri odosielani dat.", 5)
        except socket.timeout:
            self.logger.log("Cas vyprsal pri odosielani dat.", 5)
        except ConnectionResetError:
            print("Druha strana ukoncila spojenie.")
        self.sock.close()
