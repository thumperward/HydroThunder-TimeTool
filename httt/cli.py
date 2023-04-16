"""
CLI parser.
"""

import sys
import argparse
from .drive import Drive
from .data import HydroThunder
from .functions import csv_write, checksum_calc, write_raw


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
