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
        self.posielane_size = 10

    def vytvor_type(self, vstup):
        if not isinstance(vstup, tuple):
            vstup = (vstup,)
        result = 0
        for typ in vstup:
            result |= self.constants.types[typ]
        return bytes([result])

    def send_simple(self, typ, target):
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
            raise CheckSumError(f"CHKSUM Chyba pri{types[0]}")

        if typ in types:
            return True
        return False

    def send_data(self, typ, hdr_info, hdr_struct, raw_data):
        if raw_data is None:
            raw_data = ""
        if not isinstance(raw_data, bytes):
            raw_data = raw_data.encode()
        header = []
        header.append(self.vytvor_type(typ))
        header.append(hdr_info)
        packed_hdr = struct.pack(hdr_struct, header[0], header[1])
        data = packed_hdr + raw_data
        chksum = struct.pack("=H", self.crc.calculate(data))
        data_packed = data + chksum
        # print(data_packed)
        # print("NEW")
        self.sock.sendto(data_packed, self.target)
