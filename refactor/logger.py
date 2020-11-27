class Logger:
    def __init__(self, constants, integrity):
        self.constants = constants
        self.integrity = integrity
        self.print = True

    def get_send_sizes(self, data, level):
        if data is not None:  # je to DATA message
            velkost_paketu = len(data) + self.constants.DATA_HEADER_LEN + self.constants.CRC_LEN
            velkost_dat = len(data)
        else:  # je to INFO message
            velkost_paketu = self.constants.INFO_HEADER_LEN + self.constants.CRC_LEN
            velkost_dat = 0
        if self.integrity >= level and self.print:
            print(f"Velkost ODOSLANEHO fragmentu: {velkost_paketu}, Data: {velkost_dat}")
        return velkost_paketu, velkost_dat

    def get_recv_sizes(self, res, data, level):
        velkost_paketu = len(data)
        if "DM" in res or "DF" or "NACK" in res:  # bez datovej hlavicky a crc
            velkost_dat = len(data[self.constants.DATA_HEADER_LEN : -self.constants.CRC_LEN])
        else:  # bez info hlavicky
            velkost_dat = len(data[self.constants.INFO_HEADER_LEN : -self.constants.CRC_LEN])
        if self.integrity >= level and self.print:
            print(f"Velkost PRIJATEHO fragmentu: {velkost_paketu}, Data: {velkost_dat}")
        return velkost_paketu, velkost_dat

    def print_types(self, types, level):
        if self.integrity >= level and self.print:
            types = list(types)
            if "KA" in types:
                print(f"\nPOSLAL:{types}")
            else:
                print(f"POSLAL:{types}")

    def log(self, msg, level):
        if self.integrity >= level and self.print:
            print(msg)
