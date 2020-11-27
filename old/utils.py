import json
import os
import crcmod


class Crc:
    def __init__(self):
        self.crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)

    def calculate(self, data):
        return self.crc_func(bytes(data))

    def check(self, data, sender_chksum):
        return self.crc_func(bytes(data)) == sender_chksum


class Constants:
    def __init__(self):
        self.CHYBA = 50
        self.BEZ_CHYBY = 0
        with open("constants.json", "r") as file:
            self.types = json.load(file)


class CheckSumError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)


class Logger:
    pass


def get_network_data(uzol):
    while True:
        try:
            if uzol == "client":
                ip = input("IP Adresa: ")
            port = int(input("Port: "))
        except ValueError:
            print("Nespravny vstup.")
        else:
            return port if uzol == "server" else (ip, port)


def get_input(keep_alive_check=0):
    if keep_alive_check is False:
        print("Spojenie uz bolo ukoncene. Ak chce posielat, obnovte ho.")
        return None, None
    while True:
        try:
            max_fragment_size = int(input("Maximalna velkost fragmentov dat(1-1468): "))
            if max_fragment_size < 1 or max_fragment_size > 1468:
                raise ValueError
            odosielane_data = input("Odoslat: [sprava], [subor]: ")
            if odosielane_data not in ("sprava", "subor"):
                raise ValueError
            if odosielane_data == "sprava":
                sprava = input("Zadajte spravu: ")
                odosielane_data = (odosielane_data, sprava)
            elif odosielane_data == "subor":
                file_name = input("Cesta k suboru: ").replace("\\", "/")
                odosielane_data = (odosielane_data, file_name)
                if not os.path.exists(file_name):
                    raise IOError
        except IOError:
            print("Subor neexistuje.")
        except ValueError:
            print("Nespravny vstup.")
        else:
            return max_fragment_size, odosielane_data
