import os
from server import Server
from utils import Crc, Constants

if __name__ == "__main__":
    if os.path.exists("kjut.png"):
        os.remove("kjut.png")
        print("Stare kjut.png odstranene")
    else:
        print("The file does not exist")
    print("server")
    crc = Crc()
    constants = Constants()
    try:
        port = int(input("Zadajte port: "))
    except ValueError:
        print("Nespravny vstup.")
    else:
        server = Server(crc.calculate_crc, constants, port)
        server.listen()