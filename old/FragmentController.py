import math

class FragmentController:
    def __init__(self, pocet_fragmentov, velkost_bloku):
        self.good_fragments = 0
        self.good_block_len = 0
        self.block_counter = 0
        self.block_data = [None] * velkost_bloku
        self.posledny_block_size = math.ceil(pocet_fragmentov % velkost_bloku)
        self.expected_ids = list(range(velkost_bloku))
        self.DOPLN_POSLEDNY = 2
        self.timeout = False

    def reset(self, posielane_size):
        self.good_block_len = 0
        self.block_counter = 0
        self.block_data = [None] * posielane_size
        self.expected_ids = list(range(posielane_size))

    def posledny_block(self, pocet_fragmentov):
        # prva cast ci je to posledny block, druha cast ci je to posledny pkt v bloku ALEBO nastal timeout
        return self.good_fragments >= pocet_fragmentov - self.posledny_block_size and (
            (self.block_counter == self.posledny_block_size) or self.timeout
        )

    def check_block(self, pocet_fragmentov, posielane_size):
        dopln, zapis = 0, 0
        if self.posledny_block(pocet_fragmentov):
            print("posledny block")
            zapis = 1
            if self.good_block_len != self.posledny_block_size:
                dopln = self.DOPLN_POSLEDNY
                print("Treba doplnit z posledneho blocku")
            return (zapis, dopln)

        if self.block_counter == posielane_size or self.timeout:
            zapis = 1
            if self.good_block_len != posielane_size:
                dopln = 1
        return (zapis, dopln)