import json
import os
import socket
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
        self.DOPLN = 2
        self.DATA_HEADER_LEN = 5
        self.INFO_HEADER_LEN = 1
        self.CRC_LEN = 2
        with open("constants.json", "r") as file:
            self.types = json.load(file)


class CheckSumError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)


def get_network_data(uzol):
    while True:
        try:
            if uzol == "client":
                ip = input("IP Adresa: ")
                if ip != "localhost":
                    socket.inet_aton(ip)
            if uzol == "server":
                path = input("Zadajte priecinok kam sa budu ukladat data: ")
                if not os.path.exists(path):
                    vstup = input("Priecinok neexistuje, vytvorit?[y/n]: ")
                    if vstup == "y":
                        os.mkdir(path)
                    else:
                        continue
            port = int(input("Port: "))
            if not 0 < port < 65536:
                print("Neplatny port.")
                continue
        except ValueError:
            print("Nespravny vstup.")
        except socket.error:
            print("Neplatna IP adresa")
        else:
            return (path, port) if uzol == "server" else (ip, port)


def get_input(keep_alive_check=0):
    if keep_alive_check is False:
        print("Spojenie uz bolo ukoncene. Ak chcete posielat, obnovte ho.")
        return None, None, None
    while True:
        try:
            max_fragment_size = int(input("Maximalna velkost fragmentov dat(1-1465): "))
            if max_fragment_size < 1 or max_fragment_size > 1465:
                raise ValueError("Zadali ste fragment size mimo range.")
            print("Pre ukoncenie napiste [quit]")
            odosielane_data = input("Odoslat: [sprava], [subor]: ")
            if "quit" in odosielane_data:
                return None, None, None
            if odosielane_data not in ("sprava", "subor"):
                raise ValueError("Nespravny vstup")
            if odosielane_data == "sprava":
                sprava = input("Zadajte spravu: ")
                odosielane_data = (odosielane_data, sprava)
            elif odosielane_data == "subor":
                file_name = input("Cesta k suboru: ").replace("\\", "/")
                odosielane_data = (odosielane_data, file_name)
                if not os.path.exists(file_name):
                    raise IOError
            chyba = int(input(r"Zadajte [%] chybnych packetov. [-X] pre pokazenie X teho packetu: "))
        except IOError:
            print("Subor neexistuje.")
        except ValueError as e:
            if "invalid" in str(e):
                print("Musi to byt cele ciselko.")
            else:
                print(e)
        else:
            return max_fragment_size, odosielane_data, chyba
