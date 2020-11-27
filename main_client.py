import utils
from client import Client

if __name__ == "__main__":
    print("client")
    crc = utils.Crc()
    constants = utils.Constants()

    # ip = "192.168.100.10"
    ip = "localhost"
    port = 5015
    max_fragment_size = 1465
    chyba = 50
    s = input()
    odosielane_data = ("subor", "kjut.png")
    """
    odosielane_data = (
        "sprava",
        # s,
        "testujem dlhu parnu spravu",
    )
    """

    client = Client(crc, constants, (ip, port), max_fragment_size, odosielane_data, chyba)
    client.run()
    # """
