import socket
import struct
import os
import math
import crcmod


class Client:
    def __init__(self):
        UDP_IP = "192.168.100.20"
        UDP_PORT = 5008
        # MESSAGE =  input("Vasa sprava: ")
        buf = 2000
        file_name = input("Nazov suboru: ")
        fileSize = os.stat(file_name).st_size
        print("velkost suboru: " + str(fileSize))
        pocetFragmentov = math.ceil(fileSize / buf)
        print(f"pocet fragmentov{pocetFragmentov}: ")
        typ = b"1"
        crc16_func = crcmod.mkCrcFun(0x18005, initCrc=0, xorOut=0x0000)

        # header = "1"
        addr = (UDP_IP, UDP_PORT)

        print("UDP target IP: %s" % UDP_IP)
        print("UDP target port: %s" % UDP_PORT)
        # print("message: %s" % MESSAGE)

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        encodedData = file_name.encode("utf-8")
        chksum = crc16_func(encodedData)
        header = struct.pack("=cH", typ, chksum)
        data = header + encodedData

        s.sendto(data, addr)

        f = open(file_name, "rb")
        data = f.read(buf)
        cntr = 1
        while data:
            if s.sendto(data, addr):
                print("sending ..." + str(cntr) + "/" + str(pocetFragmentov))
                data = f.read(buf)
                cntr += 1
        s.close()
        f.close()
        print("Finished..")