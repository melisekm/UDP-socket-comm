import socket
import struct
import os


class Client:
    def __init__(self):
        UDP_IP = "192.168.100.20"
        UDP_PORT = 5006
        # MESSAGE =  input("Vasa sprava: ")
        buf = 1024
        file_name = input("Nazov suboru: ")
        fileSize = os.stat(file_name).st_size
        print("velkost suboru: " + str(fileSize))
        pocetFragmentov = str(int(fileSize / buf))
        print("pocet fragmentov : " + pocetFragmentov)

        addr = (UDP_IP, UDP_PORT)

        print("UDP target IP: %s" % UDP_IP)
        print("UDP target port: %s" % UDP_PORT)
        # print("message: %s" % MESSAGE)

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP

        s.sendto(file_name.encode("utf-8"), addr)

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