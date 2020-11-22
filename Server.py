import struct
import socket
from uzol import Uzol
from utils import CheckSumError, FragmentInfo


class Server(Uzol):
    def __init__(self, crc, constants, port):
        super().__init__(crc, constants)
        self.sock.bind(("localhost", port))
        self.crc = crc
        self.constants = constants
        self.buffer = 1500
        self.pocet_fragmentov = None
        self.nazov_suboru = None
        self.output = None

    def recv_fragment(self, data, block_data):
        unpacked_hdr = struct.unpack("=cH", data[:3])
        fragment_id = unpacked_hdr[1]
        raw_data = data[3:-2].decode()
        block_data[fragment_id] = raw_data
        print(f"Fragment: {fragment_id}/10 prisiel v poriadku.")

    def send_nack(self, corrupted_ids):
        data = 0
        for i in corrupted_ids:
            data |= 1 << i
        self.send_data("NACK", data, "=cH", None)

    def obtain_corrupted(self, block_data):
        corrupted_ids = []
        for idx, fragment in enumerate(block_data):
            if fragment is None:
                corrupted_ids.append(idx)
        bad_count = len(corrupted_ids)
        print(f"Je potrebne si vyziadat: {bad_count} fragmentov")
        print(f"Ich ID su:{corrupted_ids}")

        self.send_nack(corrupted_ids)

        recvd_good = 0
        block_data = [None * 10]
        while recvd_good != bad_count:
            data = self.sock.recvfrom(self.buffer)[0]
            sender_chksum = struct.unpack("=H", data[-2:])
            if not self.crc.check(data[:-2], sender_chksum):
                print("Opatovny checksum error v znovuvyziadanom fragmente.")
                raise CheckSumError
                # TODO Doriesit

            self.recv_fragment(data, block_data)

            recvd_good += 1

        return block_data

    def skontroluj_block(self, f_info, posielane_size, subor):

        zapis, dopln = f_info.check_block(self.pocet_fragmentov, posielane_size)
        if dopln:
            print("Je potrebne doplnit data")
            obtained = self.obtain_corrupted(f_info.block_data)
            dopln_data(f_info.block_data, obtained)

        if zapis:
            print("Koniec bloku, zapisujem data")
            f_info.reset(posielane_size)
            if self.nazov_suboru is not None:
                zapis_data(self.output, f_info.block_data)
            else:
                self.output += f_info.block_data
            self.send_simple("ACK", self.target)

    def recv_data(self):
        if self.nazov_suboru is not None:
            self.output = open("server/" + self.nazov_suboru)
        else:
            self.output = ""
        posielane_size = 10
        self.sock.settimeout(4)
        f_info = FragmentInfo(self.pocet_fragmentov, posielane_size)

        while f_info.good_fragments != self.pocet_fragmentov:
            try:
                data = self.sock.recvfrom(self.buffer)[0]
                sender_chksum = struct.unpack("=H", data[-2:])
                if not self.crc.check(data[:-2], sender_chksum):
                    print(f"NESEDI CHECKSUM v{f_info.block_counter}/10.")
                    continue

                self.recv_fragment(data, f_info.block_data)
                print(f"Celkovo dostal:{f_info.good_fragments}/{self.pocet_fragmentov}")

                f_info.good_fragments += 1
                f_info.good_block_len += 1

                self.skontroluj_block(f_info, posielane_size)

                f_info.block_counter += 1
            except socket.timeout:
                print(f"Cas vyprsal pri fragmentID:{f_info.block_counter}")
                print(f"Celkovo:{f_info.good_fragments}/{self.pocet_fragmentov}")

        subor.close()

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
            elif "DM" in types:
                print("Bude sa prijmat sprava.")
            self.send_simple("ACK", self.target)

        except CheckSumError:
            # dorobit ?RIES
            print("Poskodeny packet, chyba pri init sprave INIT")
            raise
        except socket.timeout:
            print("Cas vyprsal pri info pkt INIT")
            raise

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.buffer)
            self.sock.settimeout(2)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.buffer)
        except CheckSumError:
            print("Poskodeny packet, chyba pri nadviazani spojenia")
            raise
        except socket.timeout:
            print("Cas vyprsal pri inicializacii")
            raise

    def listen(self):
        try:
            self.nadviaz_spojenie()
            self.recv_info()
            self.recv_data()
        except CheckSumError:
            print("Poskodeny packet.")
            raise
        except socket.timeout:
            print("Uplynul cas")
            raise
        self.sock.close()


def zapis_data(subor, block_data):
    for data in block_data:
        subor.write(data)


def dopln_data(obtained_old, obtained_new):
    for i, new_fragment in enumerate(obtained_new):
        if new_fragment is not None:
            obtained_old[i] = new_fragment
    return obtained_old