class Logger:
    def __init__(self, constants, integrity):
        self.constants = constants
        self.integrity = integrity
        self.print_ka = True

    def get_send_sizes(self, data, level):
        if self.integrity >= level:
            if data is not None:  # je to INFO message
                velkost_paketu = len(data) + self.constants.DATA_HEADER_LEN + self.constants.CRC_LEN
                velkost_dat = len(data)
                print(f"Celkova velkost ODOSLANEHO fragmentu: {velkost_paketu}, Data: {velkost_dat}")
            else:  # je to INFO message
                velkost_paketu = self.constants.INFO_HEADER_LEN + self.constants.CRC_LEN
                velkost_dat = 0
                print(f"Celkova velkost ODOSLANEHO fragmentu: {velkost_paketu}, Data: 0")
        return velkost_paketu, velkost_dat

    def get_recv_sizes(self, res, data, level):
        if self.integrity >= level:
            velkost_paketu = len(data)
            if "DM" in res or "DF" or "NACK" in res:
                velkost_dat = len(data[self.constants.DATA_HEADER_LEN : -self.constants.CRC_LEN])
                print(f"Celkova velkost PRIJATEHO fragmentu: {velkost_paketu}, Data: {velkost_dat }")
            else:
                velkost_dat = len(data[self.constants.INFO_HEADER_LEN : -self.constants.CRC_LEN])
                print(f"Celkova velkost PRIJATEHO fragmentu: {velkost_paketu}, Data: {velkost_dat}")
        return velkost_paketu, velkost_dat

    def print_types(self, types, level):
        if self.integrity >= level:
            types = list(types)
            if "KA" in types and self.print_ka:
                print(f"\nPOSLAL:{types}")
            else:
                print(f"POSLAL:{types}")

    def log(self, msg, level):
        if self.integrity >= level:
            print(msg)
