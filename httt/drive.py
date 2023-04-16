"""
Drive structure.
"""

import csv
from .data import HydroThunder, FieldData
from .functions import get_file_size, btime, timeb, generic_write


class Drive:
    """
    Object for wrapping a drive, disk image, or raw data block.
    """

    def __init__(self, filename, args):
        # May be filepath, drive block device, or raw
        self.filename = str(filename)
        size = int(get_file_size(self.filename))
        self.raw = size <= FieldData.size

        self.blocks = [
            0 if self.raw else size - FieldData.start_offset[0],
            0 if self.raw else size - FieldData.start_offset[1],
        ]

        print(
            f"Reading drive: {self.filename}\nSize: {size}\n"
            f"Raw: {self.raw}\nBlock Addr: {self.blocks[args.block]}"
        )
        self.times = None
        self.time_bytes = None
        self.splits = None
        self.split_bytes = None

    def read_times(self, args):
        """
        Read times from file.
        """
        self.times = []
        with open(self.filename, "rb") as file_to_read:
            # Seek to first initial in filename
            file_to_read.seek(
                self.blocks[args.block]+FieldData.times_offset)
            scores = 0
            while scores < FieldData.time_count:
                boat = file_to_read.read(1)  # read boat
                # print (boat_LUT[boat])
                initials = str(file_to_read.read(3), "ascii")  # read initials
                # print (initials)
                # read four bytes for float representing time in seconds
                # Note: Game rounds weirdly and these results may differ
                timestamp = btime(file_to_read.read(4))

                self.times.append({
                    "Track": HydroThunder.tracks[scores-(scores % 10)],
                    "Initials": initials,
                    "Boat": HydroThunder.boats[boat],
                    "Timestamp": timestamp
                })
                scores += 1

        # print(str(self.times))

    def load_times(self, csv_file, args):
        """
        Load time data from a CSV file.
        """

        self.times = []
        with open(csv_file, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            self.times.extend(iter(reader))
        self.time_bytes = bytearray()
        if self.times is None:
            self.read_times(args)

        for row in self.times:
            self.time_bytes += HydroThunder.iboats[row["Boat"]]
            self.time_bytes += row["Initials"].ljust(3).encode("ascii")
            self.time_bytes += timeb(row["Timestamp"])
        # print(str(self.times))

    def read_splits(self, args):
        """
        Read split times from a file.
        """

        self.splits = []
        with open(self.filename, "rb") as file_to_read:
            # Seek to first initial in filename
            file_to_read.seek(
                self.blocks[args.block]+FieldData.split_offset)
            split = 0
            while split < FieldData.split_count:
                split_1 = btime(file_to_read.read(4))
                split_2 = btime(file_to_read.read(4))
                split_3 = btime(file_to_read.read(4))
                split_4 = btime(file_to_read.read(4))
                split_5 = btime(file_to_read.read(4))

                self.splits.append({
                    "Track": HydroThunder.tracks[split*10], "Split 1": split_1,
                    "Split 2": split_2, "Split 3": split_3, "Split 4": split_4, "Split 5": split_5
                })
                split += 1

        # print(str(self.splits))

    def load_splits(self, csv_file, args):
        """
        Load split times from a CSV file.
        """

        self.splits = []
        with open(csv_file, newline='', encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            self.splits.extend(iter(reader))
        self.byte_splits(args)
        # print(str(self.splits))

    def byte_splits(self, args):
        """
        Get byte splits.
        """
        self.split_bytes = bytearray()
        if self.splits is None:
            self.read_splits(args)

        for row in self.splits:
            self.split_bytes += timeb(row["Split 1"])
            self.split_bytes += timeb(row["Split 2"])
            self.split_bytes += timeb(row["Split 3"])
            self.split_bytes += timeb(row["Split 4"])
            self.split_bytes += timeb(row["Split 5"])

        return self.split_bytes
        # print(self.split_bytes.hex(" "))

    def write(self, drive, args):
        """
        Write to drive.
        """
        generic_write(drive.filename, self.filename, args)
