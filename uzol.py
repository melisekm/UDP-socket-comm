import struct
import socket
import random
from logger import Logger


class Uzol:
    """Predstavuje client/server."""

    def __init__(self, crc, constants):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.crc = crc
        self.constants = constants
        self.velkost_bloku = 10  # velkost posielaneho bloku
        self.recv_buffer = 1500
        self.target = None  # komu posielame data
        self.typ = None  # typ prave odosielanej/prijmanej spravy
        self.logger = Logger(self.constants, 10)

    def vytvor_type(self, vstup, data=None):
        """Transformuje zadany string/tuple na 1B cislo v bytes formate."""
        if not isinstance(vstup, tuple):
            vstup = (vstup,)  # aby sme mohli iterovat
        result = 0
        for typ in vstup:
            result |= self.constants.types[typ]

        self.logger.print_types(vstup, 0)
        self.logger.get_send_sizes(data, 0)

        return bytes([result])

    def get_type(self, types, data):
        """Transformuje prijaty 1B typ na list STR typov."""
        res = []
        for pkt_type in types:  # prijate
            for global_type in self.constants.types.items():  # konstanty
                if pkt_type & global_type[1]:
                    res.append(global_type[0])

        self.logger.log(f"PRIJAL:{res}", 0)
        self.logger.get_recv_sizes(res, data, 0)

        return res

    def send_simple(self, typ, target):
        """Odosle jednoduchu spravu s typom bez dat."""
        hdr = self.vytvor_type(typ)
        chksum = self.crc.calculate(hdr)
        packed = struct.pack("=cH", hdr, chksum)
        data = packed
        self.sock.sendto(data, target)

    def recv_simple(self, expected_typ, buffer):
        """Prijme jednuchu spravu bez dat, len s Type na zaklade vstupu."""
        data, addr = self.sock.recvfrom(buffer)
        if self.target is None:
            self.target = addr  # pre server ak este nevie skym komunikuje
        recvd_type = struct.unpack("=c", data[:1])[0]  # otvor hlavicku c type, H CRC
        recvd_types = self.get_type(recvd_type, data)  # zisti o aky typ sa jedna
        if not skontroluj_type(expected_typ, recvd_types):
            self.logger.log("Prijal nieco ine ako ocakaval.", 5)
            return None
        recvd_chksum = struct.unpack("=H", data[-2:])[0]
        if not self.crc.check(recvd_type, recvd_chksum):  # porovnaj crc
            self.logger.log(f"CHKSUM Chyba pri{recvd_types}", 6)
            return None
        return data

    def send_data(self, typ, hdr_info, hdr_struct, raw_data, chyba):
        """
        posle data vo formate, TYP, INFO, DATA, CRC
            typ: co sa posiela: STR/TUPLE of STR
            hdr_info: pocet fragmentov{4B}/fragment id{4B}, INT
            hdr_sturct: forma odosielanych dat, =cI, STR
            raw_data: None || encoded data
            chyba: 0 ak posielame bez chyby, viac ako 0 - sanca na chksum error pri odosielani
        """
        pokaz_checksum = 0
        if raw_data is None:
            raw_data = ""
        if not isinstance(raw_data, bytes):
            raw_data = raw_data.encode()
        if chyba:
            pokaz_checksum = random.randint(0, 100) <= chyba  # ak je menej tak vrati 1
        type_to_send = self.vytvor_type(typ, raw_data)
        packed_hdr = struct.pack(hdr_struct, type_to_send, hdr_info)
        data = packed_hdr + raw_data
        chksum = struct.pack("=H", self.crc.calculate(data))
        if pokaz_checksum:
            chksum = struct.pack("=H", self.crc.calculate(data) + 1)
        data_packed = data + chksum
        self.sock.sendto(data_packed, self.target)

    def recvfrom(self):
        """
        Wrapper pre recvfrom s CRC kontrolou
        Vrati data, ak paket nebol poskoedny inak None
        """
        data = self.sock.recvfrom(self.recv_buffer)[0]
        recvd_chksum = struct.unpack("=H", data[-2:])[0]
        if not self.crc.check(data[:-2], recvd_chksum):  # porovnaj crc
            return None
        return data


def skontroluj_type(expected_typ, recvd_types):
    """Porovna prijaty typ s ocakavanym."""
    if not isinstance(expected_typ, tuple):
        expected_typ = (expected_typ,)
    for typ in expected_typ:
        if typ not in recvd_types:
            return False
    return True
