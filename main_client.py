import os
from utils import Crc, Constants
from client import Client

if __name__ == "__main__":
    print("client")
    crc = Crc()
    constants = Constants()
    # prvy while - client
    """
    try:
        ip = input("IP Adresa: ")
        port = int(input("Port: "))
        # druhy while - rovnake spojenie

        max_fragment_size = int(input("Maximalna velkost fragmentov dat(1-1468): "))
        if max_fragment_size < 1 or max_fragment_size > 1468:
            raise ValueError

        odosielane_data = input("Odoslat: [sprava], [subor]: ")
        if odosielane_data not in ("sprava", "subor"):
            raise ValueError
        if odosielane_data == "sprava":
            sprava = input("Zadajte Spravu: ")
            odosielane_data = (odosielane_data, sprava)
        elif odosielane_data == "subor":
            file_name = input("Cesta k suboru: ")
            odosielane_data = (odosielane_data, file_name)
        if not os.path.exists(file_name):
            raise IOError
    except ValueError:
        print("Nespravny vstup.")
    except IOError:
        print("Subor neexistuje.")
    else:
        client = Client(crc.calculate_crc, constants, (ip, port), max_fragment_size, odosielane_data)
        client.send()
    """
    # """
    ip = "localhost"
    port = 5014
    max_fragment_size = 1
    input()
    odosielane_data = ("subor", "kjut.png")

    client = Client(crc, constants, (ip, port), max_fragment_size, odosielane_data)
    client.send()
    # """
