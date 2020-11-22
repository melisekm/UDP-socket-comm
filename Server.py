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
        self.typ_dat = None

    def recv_fragment(self, data, block_data):
        unpacked_hdr = struct.unpack("=cH", data[:3])
        # Type kontrola?
        fragment_id = unpacked_hdr[1]
        raw_data = data[3:-2]
        block_data[fragment_id] = raw_data
        print(f"Fragment: {fragment_id}/9 prisiel v poriadku.")

    def send_nack(self, corrupted_ids):
        data = 0
        for i in corrupted_ids:
            data |= 1 << i
        print("POSLAL:NACK")
        self.send_data("NACK", data, "=cH", None, self.constants.BEZ_CHYBY)

    def obtain_corrupted(self, f_info, dopln):
        corrupted_ids = []
        for idx, fragment in enumerate(f_info.block_data):
            if dopln == 2 and idx >= f_info.posledny_block_size:  # DOPLN_POSLDNY == 2
                break
            if fragment is None:
                corrupted_ids.append(idx)

        bad_count = len(corrupted_ids)
        print(f"Je potrebne si vyziadat: {bad_count} fragmentov")
        print(f"Ich ID su:{corrupted_ids}")

        self.send_nack(corrupted_ids)

        recvd_good = 0
        block_data = [None] * 10
        while recvd_good != bad_count:
            data = self.sock.recvfrom(self.buffer)[0]
            sender_chksum = struct.unpack("=H", data[-2:])[0]
            if not self.crc.check(data[:-2], sender_chksum):
                raise CheckSumError("Opatovny checksum error v znovuvyziadanom fragmente.")
                # TODO Doriesit

            self.recv_fragment(data, block_data)

            f_info.good_fragments += 1  # VSETKY
            f_info.good_block_len += 1  # OK V BLOKU
            print(f"Celkovo dostal:{f_info.good_fragments}/{self.pocet_fragmentov-1}")
            recvd_good += 1
        # self.send_simple("ACK", self.target)
        return block_data

    def skontroluj_block(self, f_info, output):
        zapis, dopln = f_info.check_block(self.pocet_fragmentov, self.posielane_size)
        if dopln:
            print("Je potrebne doplnit data")
            obtained = self.obtain_corrupted(f_info, dopln)
            dopln_data(f_info.block_data, obtained)

        if zapis:
            print("Koniec bloku, zapisujem data")
            zapis_data(self.typ_dat, output, f_info.block_data)
            f_info.reset(self.posielane_size)
            self.send_simple("ACK", self.target)

    def recv_data(self):
        if self.typ_dat == "F":
            output = open("server/" + self.nazov_suboru, "wb")
        else:
            output = ""
        self.sock.settimeout(10)
        f_info = FragmentInfo(self.pocet_fragmentov, self.posielane_size)

        while f_info.good_fragments != self.pocet_fragmentov:
            try:
                data = self.sock.recvfrom(self.buffer)[0]
                sender_chksum = struct.unpack("=H", data[-2:])[0]
                if not self.crc.check(data[:-2], sender_chksum):
                    # print(data)
                    print(f"NESEDI CHECKSUM v {f_info.block_counter}/9.")
                    f_info.block_counter += 1
                    if f_info.block_counter == self.posielane_size:
                        self.skontroluj_block(f_info, output)
                    continue

                self.recv_fragment(data, f_info.block_data)
                print(f"Celkovo SPRAVNYCH dostal:{f_info.good_fragments}/{self.pocet_fragmentov-1}")

                f_info.good_fragments += 1  # VSETKY
                f_info.good_block_len += 1  # OK V BLOKU
                f_info.block_counter += 1  # CELKOVO V BLOKU

                self.skontroluj_block(f_info, output)

            except socket.timeout:
                print(f"Cas vyprsal pri fragmentID:{f_info.block_counter}")
                print(f"Celkovo:{f_info.good_fragments}/{self.pocet_fragmentov-1}")
                try:
                    self.skontroluj_block(f_info, output)
                except socket.timeout:
                    print("Vyprsal cas pri opatovnom ziadani.")
                    raise
        if self.typ_dat == "F":
            print("Subor prijaty. Cesta:..")
            output.close()
        else:
            print("Sprava prijata.")
            print(output)

    # TODOdorobit daj mu sancu este ak pride zly
    def recv_info(self):
        try:
            data = self.sock.recvfrom(self.buffer)[0]
            sender_chksum = struct.unpack("=H", data[-2:])[0]
            if not self.crc.check(data[:-2], sender_chksum):
                raise CheckSumError("CheckSum error pri RECV INFO")
            unpacked_hdr = struct.unpack("=ci", data[:5])
            types = self.get_type(unpacked_hdr[0])

            self.pocet_fragmentov = unpacked_hdr[1]
            print(f"POCET:FRAGMENTOV:{self.pocet_fragmentov}")

            if "DF" in types:
                self.nazov_suboru = data[5:-2].decode()
                self.typ_dat = "F"
                print(f"NAZOV SUBORU:{self.nazov_suboru}")
            elif "DM" in types:
                self.typ_dat = "M"
                print("Bude sa prijmat sprava.")
            self.send_simple("ACK", self.target)

        except CheckSumError as e:
            print(e.msg)
            raise
        except socket.timeout:
            print("Cas vyprsal pri info pkt INIT")
            raise

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.buffer)
            self.sock.settimeout(10)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.buffer)
        except CheckSumError as e:
            print(e.msg)
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
        except CheckSumError as e:
            print(e.msg)
            print("Poskodeny packet.")
        except socket.timeout:
            print("Uplynul cas")
        self.sock.close()


def zapis_data(typ_dat, output, block_data):
    if typ_dat == "F":
        for data in block_data:
            if data is None:
                break
            output.write(data)
    else:
        output += block_data


def dopln_data(obtained_old, obtained_new):
    for i, new_fragment in enumerate(obtained_new):
        if new_fragment is not None:
            obtained_old[i] = new_fragment
