#!/usr/bin/env python3
"""uboot-match-patch.py - retarget an sm7125-mainline U-Boot image to another phone.

What it does:
  The sm7125-mainline U-Boot Android boot image carries a placeholder flattened
  device tree (FDT) appended to its kernel section. Its /chosen/match/<name>
  subnodes list the command-line strings U-Boot needs to pick a real device
  tree. This tool finds that appended FDT (last d00dfeed before the kernel
  end), parses it with a small built-in FDT reader, lists the match nodes, and
  optionally replaces androidboot.hwname=<from> with androidboot.hwname=<to>
  inside that FDT only. It never touches the ramdisk FIT (which has CRC32s).

  <to> must be the SAME LENGTH as <from>, and must be a prefix of the phone's
  real hwname so the substring match in U-Boot succeeds (e.g. from "joyeuse"
  to "excalib", a prefix of "excalibur").

  With --bootargs "..." it simulates U-Boot's rule: a node matches when every
  string in its match,bootargs list is a substring of the given command line;
  the first matching node in node order wins.

Arguments:
  IMAGE                    input Android boot image (header version 0)
  --from <name>            hwname to replace (e.g. joyeuse)
  --to <name>              replacement, same length (e.g. excalib)
  --bootargs <cmdline>     simulate matching against this command line
  -o, --output <file>      write the patched image here (required to patch)
  -h, --help               show this help

Changes: read-only on the input. Writes only the file named with -o, and
prints its SHA-256.

Example:
  ./uboot-match-patch.py u-boot.img --from joyeuse --to excalib \\
      --bootargs "msm_drm.dsi_display0=dsi_ft8756_huaxing_vid_display: androidboot.hwname=excalibur" \\
      -o u-boot-excalibur.img
"""

import hashlib
import struct
import sys

FDT_MAGIC = b"\xd0\x0d\xfe\xed"
ANDROID_MAGIC = b"ANDROID!"


def usage() -> None:
    print(__doc__.strip())


class RomError(Exception):
    pass


def read_boot_header(data: bytes):
    if len(data) < 48 or data[:8] != ANDROID_MAGIC:
        raise RomError("not an Android boot image (no ANDROID! magic)")
    (magic, kernel_size, kernel_addr, ramdisk_size, ramdisk_addr,
     second_size, second_addr, tags_addr, page_size, header_version,
     os_version) = struct.unpack("<8s10I", data[:48])
    if header_version != 0:
        raise RomError(f"only Android boot header v0 is supported (got v{header_version})")
    if page_size < 512 or page_size % 512:
        raise RomError(f"implausible page size {page_size}")
    if kernel_size == 0:
        raise RomError("kernel size is zero")
    return kernel_size, ramdisk_size, page_size


def find_appended_fdt(data: bytes, kernel_start: int, kernel_end: int):
    idx = data.rfind(FDT_MAGIC, kernel_start, kernel_end)
    if idx < 0:
        raise RomError("no FDT magic found inside the kernel section")
    if idx + 8 > len(data):
        raise RomError("FDT header runs past the end of the file")
    totalsize = struct.unpack(">I", data[idx + 4:idx + 8])[0]
    end = idx + totalsize
    if end > kernel_end or end > len(data):
        raise RomError(
            f"FDT at {idx:#x} has totalsize {totalsize}, past the kernel end {kernel_end:#x}")
    return idx, end


def _zstr(data: bytes, offset: int) -> str:
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("latin-1")


def parse_fdt(blob: bytes):
    """Return an ordered list of (path, {prop: bytes}) for a flattened device tree."""
    if len(blob) < 40:
        raise RomError("FDT too short")
    (magic, totalsize, off_struct, off_strings, off_rsv, version,
     last_comp, boot_cpu, size_strings, size_struct) = struct.unpack(">10I", blob[:40])
    if magic != 0xD00DFEED:
        raise RomError("bad FDT magic")
    if totalsize > len(blob):
        raise RomError("FDT totalsize is larger than the supplied blob")

    p = off_rsv
    while p + 16 <= totalsize:
        a, b = struct.unpack(">QQ", blob[p:p + 16])
        p += 16
        if a == 0 and b == 0:
            break

    nodes = []
    path = []
    p = off_struct
    struct_end = min(off_struct + size_struct, totalsize)
    while p + 4 <= struct_end:
        tok = struct.unpack(">I", blob[p:p + 4])[0]
        p += 4
        if tok == 1:  # FDT_BEGIN_NODE
            end = blob.index(b"\x00", p)
            name = blob[p:end].decode("latin-1")
            p = (end + 1 + 3) & ~3
            path.append(name)
            joined = "/" + "/".join(x for x in path if x)
            nodes.append((joined, {}))
        elif tok == 2:  # FDT_END_NODE
            if path:
                path.pop()
        elif tok == 3:  # FDT_PROP
            length, nameoff = struct.unpack(">II", blob[p:p + 8])
            p += 8
            prop = _zstr(blob, off_strings + nameoff)
            value = blob[p:p + length]
            p = (p + length + 3) & ~3
            if nodes:
                nodes[-1][1][prop] = value
        elif tok == 4:  # FDT_END
            break
        elif tok == 9:  # FDT_NOP
            continue
        else:
            raise RomError(f"unknown FDT token {tok} at offset {p - 4:#x}")
    return nodes


def match_nodes(nodes):
    """Return [(name, [strings])] for the /chosen/match/* subnodes, in order."""
    out = []
    for path, props in nodes:
        parts = [x for x in path.split("/") if x]
        if len(parts) == 3 and parts[0] == "chosen" and parts[1] == "match":
            raw = props.get("match,bootargs", b"")
            strings = [s.decode("latin-1") for s in raw.split(b"\x00") if s]
            out.append((parts[2], strings))
    return out


def chosen(matches, bootargs: str):
    for name, strings in matches:
        if strings and all(s in bootargs for s in strings):
            return name
    return None


def show(matches, bootargs):
    print(f"/chosen/match nodes ({len(matches)}):")
    for name, strings in matches:
        print(f"  {name}")
        for s in strings:
            print(f"    - {s}")
        if bootargs is not None and strings and all(s in bootargs for s in strings):
            print("    => matches")
    if bootargs is not None:
        got = chosen(matches, bootargs)
        print(f"selected device tree: {got or '(none)'}")


def main(argv):
    image = None
    frm = None
    to = None
    bootargs = None
    output = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            usage()
            return 0
        elif a in ("--from", "--to", "--bootargs", "-o", "--output"):
            i += 1
            if i >= len(argv):
                print(f"uboot-match-patch: {a} needs a value", file=sys.stderr)
                return 2
            if a == "--from":
                frm = argv[i]
            elif a == "--to":
                to = argv[i]
            elif a == "--bootargs":
                bootargs = argv[i]
            else:
                output = argv[i]
        elif a.startswith("-"):
            print(f"uboot-match-patch: unknown option {a}", file=sys.stderr)
            return 2
        elif image is None:
            image = a
        else:
            print(f"uboot-match-patch: unexpected argument {a}", file=sys.stderr)
            return 2
        i += 1

    if image is None:
        usage()
        return 2
    if (frm is None) != (to is None):
        print("uboot-match-patch: --from and --to must be used together", file=sys.stderr)
        return 2
    if frm is not None and len(frm) != len(to):
        print(f"uboot-match-patch: --to must be the same length as --from "
              f"({len(frm)} bytes), got {len(to)}", file=sys.stderr)
        return 2

    with open(image, "rb") as f:
        data = bytearray(f.read())

    kernel_size, ramdisk_size, page_size = read_boot_header(data)
    kernel_start = page_size
    kernel_end = kernel_start + kernel_size
    fdt_start, fdt_end = find_appended_fdt(data, kernel_start, kernel_end)
    print(f"image: {image} ({len(data)} bytes)")
    print(f"page size: {page_size}, kernel: {kernel_size} bytes "
          f"({kernel_start:#x}-{kernel_end:#x}), ramdisk: {ramdisk_size} bytes")
    print(f"appended FDT: {fdt_start:#x}-{fdt_end:#x} ({fdt_end - fdt_start} bytes)")

    blob = bytes(data[fdt_start:fdt_end])
    matches = match_nodes(parse_fdt(blob))
    if not matches:
        raise RomError("no /chosen/match nodes in the appended FDT")
    show(matches, bootargs)

    if frm is not None:
        old = b"androidboot.hwname=" + frm.encode()
        new = b"androidboot.hwname=" + to.encode()
        count = blob.count(old)
        if count == 0:
            raise RomError(f"no {old.decode()} inside the appended FDT")
        if output is None:
            print("uboot-match-patch: -o/--output is required when patching", file=sys.stderr)
            return 2
        patched_blob = blob.replace(old, new)
        data[fdt_start:fdt_end] = patched_blob
        print(f"replaced {old.decode()} -> {new.decode()} in {count} place(s)")

        new_matches = match_nodes(parse_fdt(patched_blob))
        if bootargs is not None:
            print("after patching:")
            show(new_matches, bootargs)

        with open(output, "wb") as f:
            f.write(data)
        digest = hashlib.sha256(data).hexdigest()
        print(f"wrote {output} ({len(data)} bytes)")
        print(f"sha256: {digest}")
    else:
        if output is not None:
            with open(output, "wb") as f:
                f.write(data)
            print(f"wrote {output} unchanged ({len(data)} bytes)")
            print(f"sha256: {hashlib.sha256(data).hexdigest()}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except RomError as exc:
        print(f"uboot-match-patch: {exc}", file=sys.stderr)
        sys.exit(1)
