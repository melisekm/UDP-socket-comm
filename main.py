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
            max_fragment_size, odosielane_data, chyba = utils.get_input()
            if max_fragment_size is None:
                continue
            client = Client(crc, constants, (ip, port), max_fragment_size, odosielane_data, chyba)
            client.run()
        elif vstup == "server":
            port = utils.get_network_data(vstup)
            server = Server(crc, constants, port)
            server.listen()
        elif vstup == "quit":
            break
