import struct
import socket
import random
from utils import CheckSumError

# predstavuje client/server.
class Uzol:
    def __init__(self, crc, constants):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.settimeout(60)  # defaultna doba cakania pri inicializovani
        self.crc = crc
        self.constants = constants
        self.target = None  # komu posielame data
        self.velkost_bloku = 10  # velkost posielaneho bloku

    # transformuje zadany string/tuple na 1B cislo v bytes formate
    def vytvor_type(self, vstup):
        if not isinstance(vstup, tuple):
            vstup = (vstup,)  # aby sme mohli iterovat
        result = 0
        for typ in vstup:
            result |= self.constants.types[typ]
        return bytes([result])

    # odosle jednoduchu spravu s typom bez dat
    def send_simple(self, typ, target):
        hdr = self.vytvor_type(typ)
        chksum = self.crc.calculate(hdr)
        packed = struct.pack("=cH", hdr, chksum)
        data = packed
        print(f"POSLAL:{typ}")
        self.sock.sendto(data, target)

    # transformuje prijaty 1B typ na list typov.
    def get_type(self, types):
        res = []
        for pkt_type in types:  # prijate
            for global_type in self.constants.types.items():  # konstanty
                if pkt_type & global_type[1]:
                    res.append(global_type[0])
        print(f"PRIJAL:{res}")
        return res

    # posle jednuchu spravu bez dat len s Type na zaklade vstupu.
    def recv_simple(self, expected_typ, buffer):
        data, addr = self.sock.recvfrom(buffer)
        if self.target is None:
            self.target = addr  # pre server ak este nevie skym komunikuje
        unpacked = struct.unpack("=cH", data)  # otvor hlavicku c type, H CRC
        recvd_types = self.get_type(unpacked[0])  # zisti o aky typ sa jedna
        if not self.crc.check(unpacked[0], unpacked[1]):  # porovnaj crc
            raise CheckSumError(f"CHKSUM Chyba pri{recvd_types}")

        if skontroluj_type(expected_typ, recvd_types):
            return True
        return False

    # posle data vo formate, TYP, INFO, DATA, CRC
    # typ co sa posiela: STR/TUPLE of STR
    # hdr_info: pocet fragmentov{4B}/fragment id{2B}, INT
    # hdr_sturct: forma odosielanych dat, =ci || =cH, STR
    # raw_data: None || encoded data
    # chyba: 0 ak posielame bez chyby, > 0 sanca na chksum error pri odosielani
    def send_data(self, typ, hdr_info, hdr_struct, raw_data, chyba):
        pokaz_checksum = 0
        if raw_data is None:
            raw_data = ""
        if not isinstance(raw_data, bytes):
            raw_data = raw_data.encode()
        if chyba:
            pokaz_checksum = random.randint(0, 100) <= chyba  # ak je menej tak vrati 1
        type_to_send = self.vytvor_type(typ)
        packed_hdr = struct.pack(hdr_struct, type_to_send, hdr_info)
        data = packed_hdr + raw_data
        chksum = struct.pack("=H", self.crc.calculate(data))
        if pokaz_checksum:
            chksum = struct.pack("=H", 0)
        data_packed = data + chksum
        self.sock.sendto(data_packed, self.target)


def skontroluj_type(expected_typ, recvd_types):
    if not isinstance(expected_typ, tuple):
        expected_typ = (expected_typ,)
    for typ in expected_typ:
        if typ not in recvd_types:
            return False
    return True
