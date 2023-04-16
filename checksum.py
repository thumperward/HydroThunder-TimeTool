#!/usr/bin/python3

import sys
import os
import struct
import datetime
import csv

filename=sys.argv[1]
checksum=0
print(f"opening: {str(filename)}")

with open(filename, "rb") as f:
    while (byte := f.read(1)):
        if val := int.from_bytes(byte, "big"):
            checksum+=val
            print(hex(checksum))
