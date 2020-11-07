from Server import *
from Client import *

if __name__ == "__main__":
    ktore = input()
    if ktore == "c":
        client = Client()

    else:
        server = Server()