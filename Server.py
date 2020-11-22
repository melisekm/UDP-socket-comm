import struct
import socket
from uzol import Uzol
from utils import CheckSumError


class Server(Uzol):
    def __init__(self, crc, constants, port):
        super().__init__(crc, constants)
        self.sock.bind(("192.168.100.10", port))
        self.crc = crc
        self.constants = constants
        self.buffer = 1500
        self.pocet_fragmentov = None
        self.nazov_suboru = None

    def recv_data(self):
        file = open("server/" + self.nazov_suboru)
        good_fragments = 0
        block_counter = 0
        while good_fragments != self.pocet_fragmentov:
            data = self.sock.recvfrom(self.buffer)[0]
            sender_chksum = struct.unpack("=H", data[-2:])[0]
            if not self.crc.check(data[:-2], sender_chksum):
                # TODO
                pass
            unpacked_hdr = struct.unpack("=cH", data[:3])
            types = self.get_type(unpacked_hdr[0])
            fragment_id = unpacked_hdr[1]
            raw_data = data[3:-2].decode()
            if block_counter == 10:
                # send daco
                pass
            # TODO POKRACOVAT vo vyvoji odoslatia suboru ACK NACK, bloky funkcie!!
        file.close()

    # TODOdorobit daj mu sancu este ak pride zly
    def recv_info(self):
        try:
            data = self.sock.recvfrom(self.buffer)[0]
            sender_chksum = struct.unpack("=H", data[-2:])[0]
            if not self.crc.check(data[:-2], sender_chksum):
                raise CheckSumError
            unpacked_hdr = struct.unpack("=ci", data[:5])
            types = self.get_type(unpacked_hdr[0])

            self.pocet_fragmentov = unpacked_hdr[1]
            print(f"POCET:FRAGMENTOV:{self.pocet_fragmentov}")

            if "DF" in types:
                self.nazov_suboru = data[5:-2].decode()
                print(f"NAZOV SUBORU:{self.nazov_suboru}")
            self.send_simple("ACK", self.target)

        except CheckSumError:
            # dorobit ?RIES
            print("Poskodeny packet, chyba pri init sprave INIT")
        except socket.timeout:
            print("Cas vyprsal pri info pkt INIT")

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.buffer)
            self.sock.settimeout(2)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.buffer)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
        except socket.timeout:
            print("Cas vyprsal pri inicializacii")

    def listen(self):
        self.nadviaz_spojenie()
        self.recv_info()
        self.recv_data()
        self.sock.close()
