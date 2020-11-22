import struct
import crcmod


class Crc:
    def __init__(self):
        self.crc_func = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)

    def calculate(self, data):
        return self.crc_func(bytes(data))

    def check(self, data, sender_chksum):
        return self.crc_func(bytes(data)) == sender_chksum


crc = Crc()

header = [bytes([128]), 10]
packed = struct.pack("=ci", header[0], header[1])
print(f"PACKED:{packed}")
data = packed + ("pes").encode()
print(f"DATA{data}")
chksum = crc.calculate(data)
print(f"CHKSUM:{chksum}")
chksum = struct.pack("=H", chksum)
posta = data + chksum
print(f"POSTA:{posta}")
senderC = struct.unpack("=H", posta[-2:])[0]
print(f"SENDERC:{senderC}")
unpack = struct.unpack("=ci", posta[:5])
print(f"UNPACK:{unpack}")
print(posta[5:-2])
data = posta[:-2]
print(f"DATA:{data}")
f = crc.check(data, senderC)
print(f)