import os
import struct
import socket
from uzol import Uzol
from utils import CheckSumError
from fragment_controller import FragmentController


class Server(Uzol):
    def __init__(self, crc, constants, path, port):
        super().__init__(crc, constants)
        self.path = path
        self.sock.bind(("localhost", port))
        # self.sock.bind(("192.168.100.10", port))

    def zapis_data(self, nazov_suboru, udaje):
        if nazov_suboru is None:
            print(f"Sprava prijata.\n{'*'*50}")
            print(udaje)
            print("*" * 50)
        else:
            cesta = self.path + "/" + nazov_suboru
            with open(cesta, "wb") as file:
                for data in udaje:
                    file.write(data)
            print("Subor prijaty.")
            print("Absolutna cesta:")
            print(os.path.abspath(cesta))

        self.sock.settimeout(20)
        print("Prechadzam do passive modu.")

    def send_nack(self, bad_count, corrupted_ids):
        self.send_data("NACK", bad_count, "=cI", corrupted_ids, self.constants.BEZ_CHYBY)

    def get_corrupted_ids(self, f_info, dopln):
        corrupted_ids = ""
        zaciatok_bloku = f_info.good_fragments - f_info.good_block_len
        koniec_bloku = (
            zaciatok_bloku + self.velkost_bloku if dopln != self.constants.DOPLN else zaciatok_bloku + f_info.posledny_block_size
        )
        dlzka = 0
        for idx in range(zaciatok_bloku, koniec_bloku):
            if f_info.block_data[idx] is None:
                corrupted_ids += str(idx) + ","
                dlzka += 1
        return corrupted_ids[:-1], dlzka

    def obtain_corrupted(self, f_info, dopln):
        corrupted_ids, bad_count = self.get_corrupted_ids(f_info, dopln)
        self.logger.log(f"Ich ID su:{[int(x)+1 for x in corrupted_ids.split(',')]}", 5)
        self.send_nack(bad_count, corrupted_ids)
        recvd_good = 0
        try:
            while recvd_good != bad_count:
                recvd_data = self.recvfrom()
                if recvd_data is None:
                    self.logger.log("Zahadzujem neocakavny chybny packet.", 5)
                    continue

                if self.process_fragment(recvd_data, [self.typ], f_info) == 1:  # neocakavany typ, ina chyba
                    continue
                f_info.good_fragments += 1  # VSETKY
                f_info.good_block_len += 1  # OK V BLOKU
                print(f"Celkovo SPRAVNYCH dostal:{f_info.good_fragments}/{f_info.pocet_fragmentov}\n")
                recvd_good += 1
        except socket.timeout:
            return 1
        return 0

    def skontroluj_block(self, f_info):
        zapis, dopln = f_info.check_block(self.velkost_bloku)
        if dopln:
            print("Je potrebne doplnit data.", end=" ")
            neuspech_ziadania = 0
            while self.obtain_corrupted(f_info, dopln) != 0:
                if neuspech_ziadania == 1:
                    raise socket.timeout
                neuspech_ziadania += 1

        if zapis:
            self.logger.log("Koniec bloku\n", 5)
            f_info.reset()
            self.send_simple("ACK", self.target)

    def process_fragment(self, recvd_data, expected_types, f_info):
        unpacked_type = struct.unpack("=c", recvd_data[0:1])[0]  # 1B type
        recvd_types = self.get_type(unpacked_type, recvd_data)
        if expected_types != recvd_types:
            self.logger.log(f"Prijal neocakavany typ -> {recvd_types}, ked cakal -> {expected_types}", 5)
            return 1
        unpacked_id = struct.unpack("=I", recvd_data[1 : self.constants.DATA_HEADER_LEN])[0]  # 4B fragment_id
        fragment_id = unpacked_id
        if f_info.block_data[fragment_id] is not None:
            self.logger.log(f"RETRANSMISSION.Fragment: {fragment_id + 1}/{f_info.pocet_fragmentov} prisiel ZNOVU.", 1)
            return 1
        raw_data = recvd_data[self.constants.DATA_HEADER_LEN : -2]  # vsetko ostane az po CRC
        f_info.block_data[fragment_id] = raw_data  # zapis na korektne miesto
        print(f"Fragment: {(fragment_id % self.velkost_bloku) + 1}/{self.velkost_bloku} prisiel v poriadku.")
        return 0

    def recv_fragments(self, typ, pocet_fragmentov):
        self.typ = typ
        f_info = FragmentController(pocet_fragmentov, self.velkost_bloku)
        while f_info.good_fragments != f_info.pocet_fragmentov:
            try:
                recvd_data = self.recvfrom()  # Prijmi datovy paket.
                if recvd_data is None:  # Poskodeny.
                    print(f"NESEDI CHECKSUM v {f_info.block_counter+1}/{self.velkost_bloku}.\n")

                else:
                    if self.process_fragment(recvd_data, [self.typ], f_info) == 1:
                        continue  # neocakavany typ, ina chyba
                    f_info.good_fragments += 1  # VSETKY
                    f_info.good_block_len += 1  # OK V BLOKU
                    print(f"Celkovo SPRAVNYCH dostal:{f_info.good_fragments}/{f_info.pocet_fragmentov}\n")

                f_info.block_counter += 1  # CELKOVO V BLOKU
                self.skontroluj_block(f_info)

            except socket.timeout:
                print(f"Cas vyprsal pri fragmentID:{f_info.block_counter}")
                print(f"Celkovo:{f_info.good_fragments}/{f_info.pocet_fragmentov}")
                try:
                    f_info.timeout = True
                    self.skontroluj_block(f_info)
                    f_info.timeout = False
                except socket.timeout:
                    print("Vyprsal cas pri opatovnom ziadani.")
                    raise

        if self.typ == "DM":
            res = ""
            for data in f_info.block_data:
                res += data.decode()
            return res
        return f_info.block_data

    def recv_info(self):
        while True:
            recvd_data = self.recvfrom()
            if recvd_data is None:
                self.logger.log("Prijal Neznamy pkt_chksum_err", 1)
                return (None, None)
            unpacked_hdr = struct.unpack("=c", recvd_data[:1])[0]
            types = self.get_type(unpacked_hdr, recvd_data)

            if "INIT" in types:
                self.sock.settimeout(2)
                pocet = struct.unpack("=I", recvd_data[1 : self.constants.DATA_HEADER_LEN])[0]
                self.send_simple("ACK", self.target)
                return types[1], pocet

            if "FIN" in types:
                self.send_simple("ACK", self.target)
                print("Prijal FIN spravu. Ukoncujem spojenie.")
                return "FIN", None
            if "KA" in types:
                self.send_simple("ACK", self.target)
            else:
                self.logger.log("Prijal nieco uplne ine...", 1)
        return None, None

    def recv_data(self):
        while True:
            mod, pocet_fragmentov = self.recv_info()
            if mod == "DF":
                print(f"\nPocet fragmentov nazvu suboru je: {pocet_fragmentov}")

                nazov_suboru = self.recv_fragments("DM", pocet_fragmentov)
                pocet_fragmentov_suboru = self.recv_info()[1]

                print(f"\nNazov suboru je: {nazov_suboru}\n")
                print(f"Pocet fragmentov suboru je: {pocet_fragmentov_suboru}")

                subor = self.recv_fragments("DF", pocet_fragmentov_suboru)
                self.zapis_data(nazov_suboru, subor)

            elif mod == "DM":
                print(f"\nPocet fragmentov spravy je: {pocet_fragmentov}")

                sprava = self.recv_fragments("DM", pocet_fragmentov)
                self.zapis_data(None, sprava)
            elif mod == "FIN":
                break

    def nadviaz_spojenie(self):
        try:
            self.recv_simple("SYN", self.recv_buffer)
            self.sock.settimeout(2)
            self.send_simple(("SYN", "ACK"), self.target)
            self.recv_simple("ACK", self.recv_buffer)
        except CheckSumError as e:
            self.logger.log(e.msg, 5)
            self.logger.log("Poskodeny packet, chyba pri nadviazani spojenia", 5)
            raise
        except socket.timeout:
            self.logger.log("Cas vyprsal pri inicializacii", 5)
            raise
        self.logger.log("Spojenie nadviazane.\n", 1)

    def listen(self):
        self.sock.settimeout(60)  # defaultna doba cakania pri inicializovani
        print("Listening..")
        try:
            self.nadviaz_spojenie()  # iba raz v connection, 3-Way Handshake
            self.recv_data()
        except CheckSumError as e:
            self.logger.log(e.msg, 5)
            self.logger.log("Neocakavny poskodeny packet.", 5)
        except socket.timeout:
            self.logger.log("Uplynul cas, ukoncujem spojenie", 1)
        self.sock.close()
