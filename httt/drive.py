"""
Drive structure.
"""

import os
import struct
import datetime
import csv
from .data import HydroThunder


def timeb(time_seconds):
    """
    Convert time to bytes.
    """

    return struct.pack(
        '<f',
        (
            datetime.datetime.strptime(time_seconds.strip(
            ), "%M:%S.%f") - datetime.datetime(1900, 1, 1)
        ).total_seconds()
    )


def btime(time_bytes):
    """
    Convert bytes to time.
    """

    return str(
        datetime.timedelta(seconds=round(
            struct.unpack('<f', time_bytes)[0], 2))
    )[2:][:8]


def get_file_size(filename):
    """
    Get the file size by seeking at end.
    """

    file_descriptor = os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(file_descriptor, 0, os.SEEK_END)
    finally:
        os.close(file_descriptor)


class Drive:
    """
    Object for wrapping a drive, disk image, or raw data block
    """

    def __init__(self, filename, args):
        # May be filepath, drive block device, or raw
        self.filename = str(filename)
        self.size = int(get_file_size(self.filename))
        self.raw = self.size <= HydroThunder.FieldData.size

        self.blocks = [
            0 if self.raw else self.size -
            HydroThunder.FieldData.start_offset[0],
            0 if self.raw else self.size -
            HydroThunder.FieldData.start_offset[1],
        ]

        print(
            f"Reading drive: {self.filename}\nSize: {self.size}\n"
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
                self.blocks[args.block]+HydroThunder.FieldData.times_offset)
            scores = 0
            while scores < HydroThunder.FieldData.time_count:
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
        self.byte_times(args)
        # print(str(self.times))

    def byte_times(self, args):
        """
        get time bytes.
        """
        self.time_bytes = bytearray()
        if self.times is None:
            self.read_times(args)

        for row in self.times:
            self.time_bytes += HydroThunder.iboats[row["Boat"]]
            self.time_bytes += row["Initials"].ljust(3).encode("ascii")
            self.time_bytes += timeb(row["Timestamp"])

        return self.time_bytes
        # print(self.time_bytes.hex(" "))

    def read_splits(self, args):
        """
        Read split times from a file.
        """

        self.splits = []
        with open(self.filename, "rb") as file_to_read:
            # Seek to first initial in filename
            file_to_read.seek(
                self.blocks[args.block]+HydroThunder.FieldData.split_offset)
            split = 0
            while split < HydroThunder.FieldData.split_count:
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

    def write(self, read_drive, write_drive, args):
        """
        Write to drive.
        """
        with open(read_drive.filename, "rb") as file_to_read:
            with open(self.filename, "r+b") as file_to_write:
                # Seek to block
                file_to_read.seek(read_drive.blocks[args.block])
                file_to_write.seek(write_drive.blocks[args.block])
                for section, byte_count in HydroThunder.FieldData.section_bytes.items():
                    if section == "splits" and read_drive.split_bytes:
                        file_to_write.write(read_drive.split_bytes)
                        file_to_read.seek(byte_count, 1)
                    elif (
                        section == "splits"
                        or section == "times"
                        and read_drive.time_bytes is None
                        or section != "times"
                    ):
                        file_to_write.write(file_to_read.read(byte_count))
                    else:
                        file_to_write.write(read_drive.time_bytes)
                        file_to_read.seek(byte_count, 1)
