#!/usr/bin/python3

"""
Tool for exporting and importing high score times from Hydro Thunder Arcade as CSV files.
"""

import sys
import csv
import argparse
from .drive import Drive
from .data import HydroThunder


def checksum_calc(drive, args):
    """
    Calculate checksums on a drive.
    """
    with open(drive.filename, "r+b") as file_to_check:
        file_to_check.seek(drive.blocks[args.block])
        header = file_to_check.read(8)

        if header != HydroThunder.FieldData.header:
            print(
                f"ERROR: Bad header [{header.hex(' ')}] @ {hex(drive.blocks[args.block])}"
            )

        file_to_check.read(4)
        checksum_stored = file_to_check.read(4)
        file_to_check.read(4)

        checksum = HydroThunder.FieldData.checksum_seed
        parity = 0
        int_read = int(HydroThunder.FieldData.size/4)
        for _ in range(int_read):
            next_int_bytes = file_to_check.read(4)
            next_int = int.from_bytes(next_int_bytes, "little", signed=False)
            checksum = checksum+next_int
            # Simulate overflows for uint32 type
            if checksum > 0xFFFFFFFF:
                checksum = (checksum % 0xFFFFFFFF) - 1
            # parity = parity+(next_int % 0x1)# Use mask to force overflow
            if next_int % 2 == 0:
                parity = not parity

        if checksum % 2 == 0:
            parity = not parity

        checksum = checksum + parity + args.lsb_offset  # Use mask to set parity bit

        file_to_check.seek(
            drive.blocks[args.block]+HydroThunder.FieldData.checksum_offset)
        file_to_check.write(checksum.to_bytes(4, "little", signed=False))

        print("Checksum:")
        print(f'Found: {checksum_stored.hex(" ")}')
        print(
            f'Wrote: {checksum.to_bytes(4, "little", signed=False).hex(" ")}')

        return checksum.to_bytes(4, "little", signed=False).hex(" ")


def csv_write(data, header, csv_file):
    """
    Write data to a CSV file.
    """
    with open(str(csv_file), 'w', newline='', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        for row in data:
            writer.writerow(row)


def print_input_error():
    """
    Print usage error.
    """
    print("Error, Need at least one of the following to be set:\n")
    print("    -r , --read")
    print("    -w , --write")
    print("         --write_raw\n")
    print("Cannot build data map")
    sys.exit(1)


def print_usage():
    """
    Print help.
    """
    parser = argparse.ArgumentParser(
        prog='Hydro Thunder Time Tool',
        description="""
        Reads and writes data for track times, split times, and
        settings for a Hydro Thunder Arcade machine's hard drive.
        """,
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

    return parser.parse_args()


def write_raw(args, read_drive):
    """
    Write data directly to a raw device.
    """
    write_filename = args.write_raw
    # if os.path.isfile(write_filename):
    #    # Update existing file
    #    with open(read_drive.filename, "rb") as r:
    #        with open(write_filename, "r+b") as w:
    #            #TODO - Add update file in place with minimal writes
    #            print("nope")
    # else:
    #     Write new file
    with open(read_drive.filename, "rb") as file_to_read:
        with open(write_filename, "wb") as file_to_write:
            file_to_read.seek(read_drive.blocks[args.block])
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


def main():
    """
    Main function.
    """
    # Run argument parsing
    args = print_usage()

    if args.boats:
        for boat in HydroThunder.iboats:
            print(boat)
        sys.exit(0)

    if args.map_names:
        for _, track in HydroThunder.tracks.items():
            print(track)
        sys.exit(0)

    if not args.read and not args.write and not args.write_raw:
        print_input_error()

    write_drive = Drive(args.write, args) if args.write else None
    read_drive = Drive(args.read, args) if args.read else Drive(
        args.write, args)

    read_drive.read_times(args)
    read_drive.read_splits(args)

    if args.times:
        if args.write or args.write_raw:
            read_drive.load_times(args.times, args)
        else:
            csv_write(read_drive.times, [
                "Track", "Initials", "Boat", "Timestamp"], args.times)

    if args.splits:
        if args.write or args.write_raw:
            read_drive.load_splits(args.splits, args)
        else:
            csv_write(read_drive.splits, [
                "Track", "Split 1", "Split 2", "Split 3", "Split 4", "Split 5"], args.splits)

    if args.write:
        write_drive.write(read_drive, write_drive, args)
        checksum_calc(write_drive, args)

    if args.write_raw:
        write_raw(args, read_drive)
        checksum_calc(Drive(args.write_raw, args), args)
