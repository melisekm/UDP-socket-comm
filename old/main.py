import utils
from client import Client
from server import Server

if __name__ == "__main__":
    crc = utils.Crc()
    constants = utils.Constants()
    while True:
        vstup = input("[client]/[server]/[quit]:")
        if vstup == "client":
            ip, port = utils.get_network_data(vstup)
            max_fragment_size, odosielane_data = utils.get_input()
            client = Client(crc, constants, (ip, port), max_fragment_size, odosielane_data, 50)
            client.init()
        elif vstup == "server":
            port = utils.get_network_data(vstup)
            server = Server(crc, constants, port)
            server.listen()
        elif vstup == "quit":
            break
