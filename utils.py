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
    pass
