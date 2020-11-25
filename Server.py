import os
import struct
import socket
from uzol import Uzol
from utils import CheckSumError
from FragmentController import FragmentController


class Server(Uzol):
    def __init__(self, crc, constants, port):
        super().__init__(crc, constants)
        self.sock.bind(("192.168.100.10", port))
        # self.sock.bind(("localhost", port))
        self.crc = crc
        self.constants = constants
        self.pocet_fragmentov = None
        self.nazov_suboru = None
        self.typ_dat = None  # typ prijatych dat
        self.output = None  # predstavuje subor aj prijatu spravu

    def zapis_data(self, typ_dat, block_data):
        if typ_dat == "DF":
            for data in block_data:
                if data is None:
                    break
                self.output.write(data)
        else:
            for data in block_data:
                if data is None:
                    break
                self.output += data.decode()

    def recv_fragment(self, recvd_data, block_data, expected_ids, expected_types):
        unpacked_hdr = struct.unpack("=cc", recvd_data[:2])  # Tuple, 0je type, 1,fragment id
        recvd_types = self.get_type(unpacked_hdr[0])
        if expected_types != recvd_types:
            print(f"Prijal neocakavany typ ->{recvd_types}, ked cakal ->{expected_types}")
            return 1
        fragment_id = unpacked_hdr[1][0]  # kedze je to bytes objekt dostaneme z neho prvy bajt.[0]
        if fragment_id not in expected_ids:
            print(f"RETRANSMISSION.Fragment: {fragment_id + 1}/{self.velkost_bloku} prisiel ZNOVU.")
            return 1
        raw_data = recvd_data[2:-2]  # vsetko ostane az po CRC
        block_data[fragment_id] = raw_data  # zapis na korektne miesto
        print(f"Fragment: {fragment_id + 1}/{self.velkost_bloku} prisiel v poriadku.")
        expected_ids.remove(fragment_id)
        return 0

    def send_nack(self, corrupted_ids):
        data = 0
        for i in corrupted_ids:
            data |= 1 << i
        print("POSLAL:NACK")
        self.send_data("NACK", data, "=cI", None, self.constants.BEZ_CHYBY)

    def obtain_corrupted(self, f_info, dopln):
        corrupted_ids = []
        for idx, fragment in enumerate(f_info.block_data):
            if dopln == 2 and idx >= f_info.posledny_block_size:  # DOPLN_POSLEDNY == 2
                break
            if fragment is None:
                corrupted_ids.append(idx)

        bad_count = len(corrupted_ids)
        print(f"Je potrebne si vyziadat: {bad_count} fragmentov\n")
        print(f"Ich ID su:{[x+1 for x in corrupted_ids]}")

        self.send_nack(corrupted_ids)

        recvd_good = 0
        while recvd_good != bad_count:
            data = self.sock.recvfrom(self.recv_buffer)[0]
            sender_chksum = struct.unpack("=H", data[-2:])[0]
            if not self.crc.check(data[:-2], sender_chksum):
                print("Zahadzujem neocakavny chybny packet.")
                continue

            if self.recv_fragment(data, f_info.block_data, corrupted_ids, [self.typ_dat]) == 1:
                continue

            f_info.good_fragments += 1  # VSETKY

            print(f"Celkovo SPRAVNYCH dostal:{f_info.good_fragments}/{self.pocet_fragmentov}")
            recvd_good += 1

        while not self.recv_simple("ACK", self.recv_buffer):
            pass

    def skontroluj_block(self, f_info):
        zapis, dopln = f_info.check_block(self.pocet_fragmentov, self.velkost_bloku)
        if dopln:
            print("Je potrebne doplnit data")
            self.obtain_corrupted(f_info, dopln)

        if zapis:
            print("Koniec bloku, zapisujem data\n")
            self.zapis_data(self.typ_dat, f_info.block_data)
            f_info.reset(self.velkost_bloku)
            self.send_simple("ACK", self.target)

    def recv_data(self):
        if self.typ_dat == "DF":
            ## pripadne vyrobit dls?
            self.output = open("downloads/" + self.nazov_suboru, "wb")
        else:
            self.output = ""
        f_info = FragmentController(self.pocet_fragmentov, self.velkost_bloku)

        while f_info.good_fragments != self.pocet_fragmentov:
            try:
                data = self.sock.recvfrom(self.recv_buffer)[0]
                sender_chksum = struct.unpack("=H", data[-2:])[0]
                if not self.crc.check(data[:-2], sender_chksum):
                    print(f"NESEDI CHECKSUM v {f_info.block_counter+1}/{self.velkost_bloku}.")

                else:
                    if self.recv_fragment(data, f_info.block_data, f_info.expected_ids, [self.typ_dat]) == 1:
                        continue
                    f_info.good_fragments += 1  # VSETKY
                    f_info.good_block_len += 1  # OK V BLOKU
                    print(f"Celkovo SPRAVNYCH dostal:{f_info.good_fragments}/{self.pocet_fragmentov}")

                f_info.block_counter += 1  # CELKOVO V BLOKU
                self.skontroluj_block(f_info)

            except socket.timeout:
                print(f"Cas vyprsal pri fragmentID:{f_info.block_counter}")
                print(f"Celkovo:{f_info.good_fragments}/{self.pocet_fragmentov}")
                try:
                    f_info.timeout = True
                    self.skontroluj_block(f_info)
                    f_info.timeout = False
                except socket.timeout:
                    print("Vyprsal cas pri opatovnom ziadani.")
                    raise
        if self.typ_dat == "DF":
            print("Subor prijaty.")
            print("Absolutna cesta:")
            print(os.path.abspath("downloads/" + self.nazov_suboru))
            self.output.close()
        else:
            print("Sprava prijata.")
            print(self.output)

    # TODOdorobit daj mu sancu este ak pride zly
    def recv_info(self):
        try:
            while True:
                data = self.sock.recvfrom(self.recv_buffer)[0]
                sender_chksum = struct.unpack("=H", data[-2:])[0]
                if not self.crc.check(data[:-2], sender_chksum):
                    # raise CheckSumError("CheckSum error pri RECV INFO")
                    print("Prijal Neznamy pkt_chksum_err")
                    continue
                unpacked_hdr = struct.unpack("=c", data[:1])[0]
                types = self.get_type(unpacked_hdr)
                if "INIT" in types:
                    break
                if "KA" in types:
                    self.send_simple("ACK", self.target)
                elif "FIN" in types:
                    self.send_simple("ACK", self.target)
                    return 1
                else:
                    print("Prijal nieco uplne ine...")

            self.send_simple("ACK", self.target)
            self.sock.settimeout(60)
            self.pocet_fragmentov = struct.unpack("=i", data[1:5])[0]
            print(f"POCET FRAGMENTOV:{self.pocet_fragmentov}")

            if "DF" in types:
                self.nazov_suboru = data[5:-2].decode()
                self.typ_dat = "DF"
                print(f"NAZOV SUBORU:{self.nazov_suboru}\n")
            elif "DM" in types:
                self.typ_dat = "DM"
                print("Bude sa prijmat sprava.\n")
            else:
                print("Chybny typ.")
                return 2

        except CheckSumError as e:
            print(e.msg)
            raise
        except socket.timeout:
            print("Cas vyprsal pri info pkt INIT")
            raise

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.recv_buffer)
            self.sock.settimeout(60)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError as e:
            print(e.msg)
            print("Poskodeny packet, chyba pri nadviazani spojenia")
            raise
        except socket.timeout:
            print("Cas vyprsal pri inicializacii")
            raise
        print("Spojenie nadviazane.\n")

    def listen(self):
        try:
            self.nadviaz_spojenie()  # iba raz v connection, 3-Way Handshake
            while True:
                if self.recv_info() in (1, 2):  # 0 ak ok, ine ak err
                    break
                self.recv_data()  # mod prijmania dat
                print("Prechadzam do passive modu.")
                self.sock.settimeout(60)  # vypni len ak nepride KA

        except CheckSumError as e:
            print(e.msg)
            print("Poskodeny packet.")
        except socket.timeout:
            print("Uplynul cas")
        self.sock.close()