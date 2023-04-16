"""
Utility functions.
"""

import os
import struct
import datetime
import csv
from .data import FieldData


def generic_write(read_drive, write_drive, args):
    """
    Write to file.
    """
    with open(read_drive.filename, "rb") as file_to_read:
        with open(write_drive, "r+b") as file_to_write:
            # Seek to block
            file_to_read.seek(read_drive.blocks[args.block])
            file_to_write.seek(write_drive.blocks[args.block])
            for section, byte_count in FieldData.section_bytes.items():
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


def write_raw(args, write_drive):
    """
    Write data directly to a raw device.
    """
    write_filename = args.write_raw
    # if os.path.isfile(write_filename):
    #    # Update existing file
    #    with open(write_drive.filename, "rb") as r:
    #        with open(write_filename, "r+b") as w:
    #            #TODO - Add update file in place with minimal writes # pylint: disable=fixme
    #            print("nope")
    # else:
    #     Write new file
    generic_write(write_drive.filename, write_filename, args)


def checksum_calc(drive, args):
    """
    Calculate checksums on a drive.
    """
    with open(drive.filename, "r+b") as file_to_check:
        file_to_check.seek(drive.blocks[args.block])
        header = file_to_check.read(8)

        if header != FieldData.header:
            print(
                f"ERROR: Bad header [{header.hex(' ')}] @ {hex(drive.blocks[args.block])}"
            )

        file_to_check.read(4)
        checksum_stored = file_to_check.read(4)
        file_to_check.read(4)

        checksum = FieldData.checksum_seed
        parity = 0
        int_read = int(FieldData.size/4)
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
            drive.blocks[args.block]+FieldData.checksum_offset)
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
