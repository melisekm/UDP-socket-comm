import math


class FragmentController:
    def __init__(self, pocet_fragmentov, velkost_bloku):
        self.good_fragments = 0 # celkovy pocet prijatych fragmentov, ktore boli v poriadku a budu zapisane
        self.good_block_len = 0 # pocet spravne prijatych fragmentov v danom bloku
        self.block_counter = 0 # pocet prijatych fragmentov v danom bloku(aj spravne aj nespravne)
        self.block_data = [None] * pocet_fragmentov # data, ktore budu zapisane
        self.pocet_fragmentov = pocet_fragmentov # celkovy pocet ocakavanych fragmentov
        self.posledny_block_size = math.ceil(pocet_fragmentov % velkost_bloku) # vypocet velkosti posledneho bloku
        self.DOPLN_POSLEDNY = 2 # znaci ze v poslednom bloku chybaju data
        self.timeout = False # nastal timeout, urcite potrebujeme doplnit

    def reset(self):
        self.good_block_len = 0
        self.block_counter = 0

    def posledny_block(self):
        # prva cast ci je to posledny block, druha cast ci je to posledny pkt v bloku ALEBO nastal timeout
        return self.good_fragments >= self.pocet_fragmentov - self.posledny_block_size and (
            (self.block_counter == self.posledny_block_size) or self.timeout
        )

    def check_block(self, posielane_size):
        dopln, zapis = 0, 0
        if self.posledny_block():
            zapis = 1
            if self.good_block_len != self.posledny_block_size:
                dopln = self.DOPLN_POSLEDNY
            return (zapis, dopln)

        if self.block_counter == posielane_size or self.timeout:
            zapis = 1
            if self.good_block_len != posielane_size:
                dopln = 1
        return (zapis, dopln)
