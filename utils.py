import json
import crcmod


class Crc:
    def __init__(self):
        self.crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)

    def calculate_crc(self, data):
        return hex(self.crc_func(data))


class Constants:
    def __init__(self):
        with open("constants.json", "r") as file:
            self.types = json.load(file)