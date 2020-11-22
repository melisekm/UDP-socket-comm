import json
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
        with open("constants.json", "r") as file:
            self.types = json.load(file)


class CheckSumError(Exception):
    def __init__(self, msg):
        self.msg = msg
        super().__init__(msg)


class FragmentInfo:
    def __init__(self, pocet_fragmentov, posielane_size):
        self.good_fragments = 0
        self.good_block_len = 0
        self.block_counter = 0
        self.block_data = [None] * posielane_size
        self.posledny_block_size = pocet_fragmentov // posielane_size

    def reset(self, posielane_size):
        self.good_block_len = 0
        self.block_counter = 0
        self.block_data = [None] * posielane_size

    def posledny_block(self, pocet_fragmentov):
        return (
            self.good_fragments > pocet_fragmentov - self.posledny_block_size
            and self.block_counter == self.posledny_block_size
        )

    def check_block(self, pocet_fragmentov, posielane_size):
        dopln, zapis = 0, 0
        if self.posledny_block(pocet_fragmentov):
            zapis = 1
            if self.good_block_len != self.posledny_block_size:
                dopln = 1
            return (zapis, dopln)
            
        if self.good_block_len != posielane_size:
            dopln = 1

        if self.block_counter == posielane_size:
            zapis = 1
        return (zapis, dopln)
