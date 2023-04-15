"""
Field data structure.
"""


class HydroThunder:
    """
    General data.
    """
    boats = {
        b'\x00': "Banshee",
        b'\x01': "Tidal Blade",
        b'\x02': "Rad Hazzard",
        b'\x03': "Miss Behave",
        b'\x04': "Damn the Torpedoes",
        b'\x05': "Cutthroat",
        b'\x06': "Razorback",
        b'\x07': "Thresher",
        b'\x08': "Midway",
        b'\t': "Chumdinger",
        b'\n': "Armed Response",
        b'\x0b': "Blowfish",
        b'\x0c': "Tinytanic"
    }
    iboats = {name: boat_id for boat_id, name in boats.items()}

    tracks = {
        0: "Ship Graveyard",
        10: "Lost Island",
        20: "Venice Canals",
        30: "Lake Powell",
        40: "Arctic Circle",
        50: "Nile Adventure",
        60: "N.Y. Disaster",
        70: "Greek Isles",
        80: "The Far East",
        90: "TEST - Not Accessible",
        100: "Thunder Park",
        110: "Hydro Speedway",
        120: "Castle Von Dandy - Not Accessible",
        130: "End"
    }

    class FieldData:
        """
        Field data.
        """
        start_offset = [530432, 333824]  # In bytes from true end of drive
        size = 8192  # Rough size rounded up to nice number
        # Always present
        header = bytearray(b'\x01\x00\x00\x00\x98\xba\xdc\xfe')
        checksum_offset = 12  # Bytes from data start to checksum
        checksum_seed = 0xFEDCBAF2
        section_bytes = {"header": 12, "checksum": 4, "static1": 4, "config": 360,
                         "times": 1040, "static2": 4, "splits": 260, "audit": 6508}
        config_offset = 20
        times_offset = 380
        time_count = 130
        split_offset = 1424
        split_count = 13
        audit_offset = 1684
