#!/usr/bin/env python3
"""squash-mdt.py - join Qualcomm split firmware (name.mdt + name.bNN) into one .mbn.

What it does:
  Reads the ELF header and program headers from name.mdt, then places the file
  bytes of every loadable segment (p_filesz > 0) from its sibling name.bNN (NN
  is the two-digit program-header index) at the segment's p_offset. It errors
  on a missing part or a part whose size does not match p_filesz. The result is
  padded to a 4096-byte boundary, like pil-squasher produces.

  The .mdt is proprietary firmware: keep it out of public repositories.

Arguments:
  MDT                the split firmware's .mdt file
  -o, --output FILE  write the joined image here (required)
  -h, --help         show this help

Changes: read-only on the input. Writes only the file named with -o, and prints
its SHA-256.

Example:
  ./squash-mdt.py modem.mdt -o modem.mbn
"""

import hashlib
import os
import struct
import sys

ALIGN = 4096


def usage() -> None:
    print(__doc__.strip())


class SquashError(Exception):
    pass


def read_program_headers(data: bytes):
    if len(data) < 20 or data[:4] != b"\x7fELF":
        raise SquashError("not an ELF file (no 7f ELF magic)")
    elf_class = data[4]
    elf_data = data[5]
    if elf_data != 1:
        raise SquashError("only little-endian firmware is supported")
    if elf_class == 1:
        if len(data) < 52:
            raise SquashError("truncated ELF32 header")
        phoff, = struct.unpack("<I", data[28:32])
        phentsize, phnum = struct.unpack("<HH", data[42:46])
        fmt = "<8I"
        size = 32
    elif elf_class == 2:
        if len(data) < 64:
            raise SquashError("truncated ELF64 header")
        phoff, = struct.unpack("<Q", data[32:40])
        phentsize, phnum = struct.unpack("<HH", data[54:58])
        fmt = "<IIQQQQQQ"
        size = 56
    else:
        raise SquashError(f"unknown ELF class {elf_class}")
    if size != phentsize and phentsize < size:
        raise SquashError(f"program header entry is too small ({phentsize} bytes)")

    out = []
    for i in range(phnum):
        off = phoff + i * phentsize
        raw = data[off:off + struct.calcsize(fmt)]
        if len(raw) < struct.calcsize(fmt):
            raise SquashError("program header table runs past the end of the .mdt")
        fields = struct.unpack(fmt, raw)
        if elf_class == 1:
            p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = fields
        else:
            p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = fields
        out.append((i, p_type, p_offset, p_filesz, p_memsz))
    return out


def main(argv):
    mdt = None
    output = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            usage()
            return 0
        elif a in ("-o", "--output"):
            i += 1
            if i >= len(argv):
                print("squash-mdt: -o needs a file name", file=sys.stderr)
                return 2
            output = argv[i]
        elif a.startswith("-"):
            print(f"squash-mdt: unknown option {a}", file=sys.stderr)
            return 2
        elif mdt is None:
            mdt = a
        else:
            print(f"squash-mdt: unexpected argument {a}", file=sys.stderr)
            return 2
        i += 1

    if mdt is None:
        usage()
        return 2
    if output is None:
        print("squash-mdt: -o/--output is required", file=sys.stderr)
        return 2
    if not os.path.isfile(mdt):
        print(f"squash-mdt: {mdt} does not exist", file=sys.stderr)
        return 2

    with open(mdt, "rb") as f:
        data = f.read()

    headers = read_program_headers(data)
    base, ext = os.path.splitext(mdt)
    if ext.lower() != ".mdt":
        print(f"squash-mdt: warning: {mdt} does not end in .mdt", file=sys.stderr)

    segments = []
    end = len(data)
    for index, p_type, p_offset, p_filesz, p_memsz in headers:
        if p_filesz == 0:
            continue
        part = f"{base}.b{index:02d}"
        if not os.path.isfile(part):
            raise SquashError(f"missing part for segment {index}: {part}")
        actual = os.path.getsize(part)
        if actual != p_filesz:
            raise SquashError(
                f"{part} is {actual} bytes, segment {index} wants {p_filesz}")
        segments.append((index, p_offset, p_filesz, part))
        end = max(end, p_offset + p_filesz)

    total = ((end + ALIGN - 1) // ALIGN) * ALIGN
    out = bytearray(total)
    out[:len(data)] = data
    for index, p_offset, p_filesz, part in segments:
        with open(part, "rb") as f:
            out[p_offset:p_offset + p_filesz] = f.read()

    with open(output, "wb") as f:
        f.write(out)
    digest = hashlib.sha256(out).hexdigest()
    print(f"joined {len(segments)} segment(s) from {os.path.basename(mdt)} into {output}")
    print(f"size: {len(out)} bytes")
    print(f"sha256: {digest}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SquashError as exc:
        print(f"squash-mdt: {exc}", file=sys.stderr)
        sys.exit(1)
