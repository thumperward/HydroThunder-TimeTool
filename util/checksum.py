#!/usr/bin/python3

"""
Calculate checksum.
"""

import sys


def main():
    """
    Calculate checksum.
    """
    filename = sys.argv[1]
    checksum = 0
    print(f"opening: {str(filename)}")

    with open(filename, "rb") as file_to_read:
        while (byte := file_to_read.read(1)):
            if val := int.from_bytes(byte, "big"):
                checksum += val
                print(hex(checksum))


if __name__ == "__main__":
    main()
