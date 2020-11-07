import socket
import struct
import crcmod

UDP_IP = "192.168.100.20"
UDP_PORT = 5007


class Server:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.buf = 1024
        self.listen()

    def listen(self):
        self.sock.settimeout(10)
        data, addr = self.sock.recvfrom(self.buf)  # buffer size is 1024 bytes
        # print("Received File:", data.decode("utf-8"))
        # f = open(data.decode("utf-8"), "wb")
        print(data)
        unpack = struct.unpack("=cH", data[:3])
        chksum = unpack[0]
        typ = unpack[1]
        crc16_func = crcmod.mkCrcFun(0x18005, initCrc=0, xorOut=0x0)
        print(f"typ:{typ}, prijaty chksum:{chksum}")
        vypocitanychksum = crc16_func(data[3:])
        print(f"vypocitany chksum:{vypocitanychksum}")
        self.sock.close()
        """
        data, addr = self.sock.recvfrom(self.buf)
        try:
            while data:
                f.write(data)
                self.sock.settimeout(2)
                data, addr = self.sock.recvfrom(self.buf)
        except:
            f.close()
            self.sock.close()
            print("File Downloaded")
        """