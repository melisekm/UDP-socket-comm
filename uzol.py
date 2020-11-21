import struct
import socket
import random
from utils import CheckSumError


class Uzol:
    def __init__(self, crc, constants):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.settimeout(60)
        self.crc = crc
        self.constants = constants
        self.target = None

    def vytvor_type(self, vstup):
        result = 0
        for typ in vstup:
            result |= self.constants.types[typ]
        return bytes([result])

    def send_simple(self, typ, target):
        if not isinstance(typ, tuple):
            typ = (typ,)
        hdr = self.vytvor_type(typ)
        chksum = self.crc.calculate(hdr)
        packed = struct.pack("=cH", hdr, chksum)
        data = packed
        print(f"POSLAL:{typ}")
        self.sock.sendto(data, target)

    def get_type(self, types):
        res = []
        for pkt_type in types:
            for global_type in self.constants.types.items():
                if pkt_type & global_type[1]:
                    res.append(global_type[0])
                    print(f"PRIJAL:{global_type[0]}")
        return res

    def recv_simple(self, typ, buffer):
        typ = (typ,)
        data, addr = self.sock.recvfrom(buffer)
        if self.target is None:
            self.target = addr
        unpacked = struct.unpack("=cH", data)
        types = self.get_type(unpacked[0])
        if not self.crc.check(unpacked[0], unpacked[1]):
            raise CheckSumError

        if typ in types:
            return True
        return False
