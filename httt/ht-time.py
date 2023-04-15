#!/usr/bin/python3

import sys
import os
import os.path
import struct
import datetime
import csv
import argparse

read_drive = None
write_drive = None
filename = None
data_csv = None
args = None


def btime(time_bytes):
    return str(datetime.timedelta(seconds=round(struct.unpack('<f', time_bytes)[0], 2)))[2:][:8]


def timeb(time_seconds):
    return struct.pack('<f', (datetime.datetime.strptime(time_seconds.strip(), "%M:%S.%f") - datetime.datetime(1900, 1, 1)).total_seconds())


def get_file_size(filename):
    """
    Get the file size by seeking at end
    """

    fd = os.open(filename, os.O_RDONLY)
    try:
        return os.lseek(fd, 0, os.SEEK_END)
    finally:
        os.close(fd)


class ht:
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

    class data:
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


class Drive:
    """
    Object for wrapping a drive, disk image, or raw data block
    """

    def __init__(self, filename):
        # May be filepath, drive block device, or raw
        self.filename = str(filename)
        self.size = int(get_file_size(self.filename))
        self.raw = self.size <= ht.data.size

        self.blocks = [
            0 if self.raw else self.size - ht.data.start_offset[0],
            0 if self.raw else self.size - ht.data.start_offset[1],
        ]

        print(
            f"Reading drive: {self.filename}\nSize: {self.size}\nRaw: {self.raw}\nBlock Addr: {self.blocks[args.block]}"
        )
        self.times = None
        self.time_bytes = None
        self.splits = None
        self.split_bytes = None

    def read_times(self):
        self.times = []
        with open(self.filename, "rb") as f:
            # Seek to first initial in filename
            f.seek(self.blocks[args.block]+ht.data.times_offset)
            scores = 0
            while scores < ht.data.time_count:
                boat = f.read(1)  # read boat
                # print (boat_LUT[boat])
                initials = str(f.read(3), "ascii")  # read initials
                # print (initials)
                # read four bytes for float representing time in seconds
                # Note: Game rounds weirdly and these results may differ
                timestamp = btime(f.read(4))

                self.times.append({"Track": ht.tracks[scores-(
                    scores % 10)], "Initials": initials, "Boat": ht.boats[boat], "Timestamp": timestamp})
                scores += 1

        # print(str(self.times))

    def load_times(self, csv_file):
        self.times = []
        with open(csv_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            self.times.extend(iter(reader))
        self.byte_times()
        # print(str(self.times))

    def byte_times(self):
        self.time_bytes = bytearray()
        if self.times is None:
            self.read_times()

        for row in self.times:
            self.time_bytes += ht.iboats[row["Boat"]]
            self.time_bytes += row["Initials"].ljust(3).encode("ascii")
            self.time_bytes += timeb(row["Timestamp"])

        return self.time_bytes
        # print(self.time_bytes.hex(" "))

    def read_splits(self):
        self.splits = []
        with open(self.filename, "rb") as f:
            # Seek to first initial in filename
            f.seek(self.blocks[args.block]+ht.data.split_offset)
            split = 0
            while split < ht.data.split_count:
                split_1 = btime(f.read(4))
                split_2 = btime(f.read(4))
                split_3 = btime(f.read(4))
                split_4 = btime(f.read(4))
                split_5 = btime(f.read(4))

                self.splits.append({"Track": ht.tracks[split*10], "Split 1": split_1,
                                   "Split 2": split_2, "Split 3": split_3, "Split 4": split_4, "Split 5": split_5})
                split += 1

        # print(str(self.splits))

    def load_splits(self, csv_file):
        self.splits = []
        with open(csv_file, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            self.splits.extend(iter(reader))
        self.byte_splits()
        # print(str(self.splits))

    def byte_splits(self):
        self.split_bytes = bytearray()
        if self.splits is None:
            self.read_splits()

        for row in self.splits:
            self.split_bytes += timeb(row["Split 1"])
            self.split_bytes += timeb(row["Split 2"])
            self.split_bytes += timeb(row["Split 3"])
            self.split_bytes += timeb(row["Split 4"])
            self.split_bytes += timeb(row["Split 5"])

        return self.split_bytes
        # print(self.split_bytes.hex(" "))

    def write(self, update):
        with open(read_drive.filename, "rb") as r:
            with open(self.filename, "r+b") as w:
                # Seek to block
                r.seek(read_drive.blocks[args.block])
                w.seek(write_drive.blocks[args.block])
                for section, byte_count in ht.data.section_bytes.items():
                    if section == "splits" and read_drive.split_bytes is not None:
                        w.write(read_drive.split_bytes)
                        r.seek(byte_count, 1)
                    elif (
                        section == "splits"
                        or section == "times"
                        and read_drive.time_bytes is None
                        or section != "times"
                    ):
                        w.write(r.read(byte_count))
                    else:
                        w.write(read_drive.time_bytes)
                        r.seek(byte_count, 1)


def checksum_calc(drive):
    with open(drive.filename, "r+b") as f:
        f.seek(drive.blocks[args.block])
        header = f.read(8)

        if (header != ht.data.header):
            print(
                f"ERROR: Bad header [{header.hex(' ')}] @ {hex(drive.blocks[args.block])}"
            )

        f.read(4)
        checksum_stored = f.read(4)
        f.read(4)

        checksum = ht.data.checksum_seed
        parity = 0
        int_read = int(ht.data.size/4)
        for _ in range(int_read):
            next_int_bytes = f.read(4)
            next_int = int.from_bytes(next_int_bytes, "little", signed=False)
            checksum = (checksum+next_int)
            # Simulate overflows for uint32 type
            if checksum > 0xFFFFFFFF:
                checksum = (checksum % 0xFFFFFFFF) - 1
            # parity = parity+(next_int % 0x1)# Use mask to force overflow
            if next_int % 2 == 0:
                parity = not (parity)

        if checksum % 2 == 0:
            parity = not (parity)

        checksum = checksum + parity + args.lsb_offset  # Use mask to set parity bit

        f.seek(drive.blocks[args.block]+ht.data.checksum_offset)
        f.write(checksum.to_bytes(4, "little", signed=False))

        print("Checksum:")
        print(f'Found: {checksum_stored.hex(" ")}')
        print("Wrote: {}".format(checksum.to_bytes(
            4, "little", signed=False).hex(" ")))

        return checksum.to_bytes(4, "little", signed=False).hex(" ")


def csv_write(data, header, csv_file):
    with open(str(csv_file), 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)

        writer.writeheader()
        for row in data:
            writer.writerow(row)


def print_input_error():
    print("Error, Need at least one of the following to be set:\n")
    print("    -r , --read")
    print("    -w , --write")
    print("         --write_raw\n")
    print("Cannot build data map")
    sys.exit(1)


def main():

    parser = argparse.ArgumentParser(
        prog='Hydro Thunder Time Tool',
        description='Reads and writes data for track times, split times, and' +
        'settings for a Hydro Thunder Arcade machine\'s hard drive.',
        epilog='Hey, you found a secret!')

    parser.add_argument('filename', nargs='?')

    # Primary function parameters
    parser.add_argument('-t', '--times', default=None,
                        help='High score times for tracks')
    parser.add_argument('-s', '--splits', default=None,
                        help='Best checkpoint split times for tracks')
    parser.add_argument('-c', '--config',
                        help='Configuration options and calibration data')
    parser.add_argument('-r', '--read', default=None,
                        help='Drive or image to read from')
    parser.add_argument('-w', '--write', default=None,
                        help='Write data to provided drive or image')
    parser.add_argument('--block', default=0, choices=[0, 1], type=int,
                        help='Override which data block to read')
    parser.add_argument('--write_raw', default=None,
                        help="Write raw data block instead of at end of drive")

    # Helpful info options
    parser.add_argument('-b', '--boats', action='store_true',
                        help='List boat names in game\'s stored order')
    parser.add_argument('-m', '--map_names', action='store_true',
                        help='List track names in game\'s stored order')
    parser.add_argument('--lsb_offset', default=0, type=int,
                        help='Fine tune checksum LSB value which can slightly vary')
    # Run argument parsing
    args = parser.parse_args()

    if args.boats:
        for boat in ht.iboats:
            print(boat)
        sys.exit(0)

    if args.map_names:
        for key, track in ht.tracks.items():
            print(track)
        sys.exit(0)

    if args.read is None and args.write is None and args.write_raw is None:
        print_input_error()
    if args.write is not None:
        print(f"Init Write: {args.write}")
        write_drive = Drive(args.write)
        if args.read is None:
            print(f"Init Read: {args.write}")
            read_drive = Drive(args.write)
    else:
        write_drive = None

    if args.read is not None or args.write is not None:
        if read_drive is None:
            print(f"Init Read: {args.read}")
            read_drive = Drive(args.read)
        read_drive.read_times()
        read_drive.read_splits()

        if args.times is not None:
            if args.write is None and args.write_raw is None:
                csv_write(read_drive.times, [
                    "Track", "Initials", "Boat", "Timestamp"], args.times)
            else:
                read_drive.load_times(args.times)

        if args.splits is not None:
            if args.write is None and args.write_raw is None:
                csv_write(read_drive.splits, [
                    "Track", "Split 1", "Split 2", "Split 3", "Split 4", "Split 5"], args.splits)
            else:
                read_drive.load_splits(args.splits)

            # Add else to use write drive as read if data CSV provided
    else:
        read_drive = None

    # bytes_times = read_drive.byte_times()
    # bytes_splits = read_drive.byte_splits()

    if args.write is not None:
        write_drive.write(read_drive)
        checksum_calc(write_drive)

    if args.write_raw is not None:
        write_filename = args.write_raw
    #    if os.path.isfile(write_filename):
    #        # Update existing file
    #        with open(read_drive.filename, "rb") as r:
    #            with open(write_filename, "r+b") as w:
    #                #TODO - Add update file in place with minimal writes
    #                print("nope")
    #    else:
        # Write new file
        with open(read_drive.filename, "rb") as r:
            with open(write_filename, "wb") as w:
                # Seek to block
                r.seek(read_drive.blocks[args.block])
                for section, byte_count in ht.data.section_bytes.items():
                    if (
                        section == "splits"
                        and read_drive.split_bytes is not None
                    ):
                        w.write(read_drive.split_bytes)
                        r.seek(byte_count, 1)
                    elif (
                        section == "splits"
                        or section == "times"
                        and read_drive.time_bytes is None
                        or section != "times"
                    ):
                        w.write(r.read(byte_count))
                    else:
                        w.write(read_drive.time_bytes)
                        r.seek(byte_count, 1)
        checksum_calc(Drive(write_filename))

    sys.exit(0)
