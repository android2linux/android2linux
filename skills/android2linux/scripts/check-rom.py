#!/usr/bin/env python3
"""check-rom.py - verify a Xiaomi fastboot ROM before flashing.

What it does:
  * Given an unpacked ROM folder (containing images/ and md5sum.xml) or the
    original .tgz, checks the archive's MD5 against the hash prefix in its
    file name (e.g. ..._933f5d8da9.tgz), checks every image listed in
    md5sum.xml, and reads flash_all.sh's product check and CURRENT_ANTI_VER.
  * With --device and/or --anti it compares those against the phone's values.
  * It warns that flash_all_lock.sh relocks the bootloader.

Arguments:
  ROM                     unpacked folder or the .tgz archive
  --device <codename>     expected device codename (e.g. excalibur)
  --anti <number>         the phone's current anti-rollback index
  -h, --help              show this help

Changes: read-only. For a .tgz it extracts to a temporary folder and removes it
again; it never touches the phone.

Exit status is non-zero if any check fails.

Example:
  ./check-rom.py rom/excalibur_V12.0.4.0_933f5d8da9.tgz --device excalibur --anti 1
"""

import hashlib
import os
import re
import shutil
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET


def usage() -> None:
    print(__doc__.strip())


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def archive_prefix(name: str) -> str | None:
    """Return the hash prefix Xiaomi puts at the end of the archive name."""
    base = os.path.basename(name)
    m = re.search(r"_([0-9a-fA-F]{6,32})\.(?:tgz|tar\.gz)$", base)
    return m.group(1).lower() if m else None


def find_rom_root(folder: str) -> str:
    """Return the folder that holds md5sum.xml, looking one level down in a tgz."""
    if os.path.isfile(os.path.join(folder, "md5sum.xml")):
        return folder
    entries = [e for e in os.listdir(folder) if os.path.isdir(os.path.join(folder, e))]
    if len(entries) == 1:
        inner = os.path.join(folder, entries[0])
        if os.path.isfile(os.path.join(inner, "md5sum.xml")):
            return inner
    return folder


def image_path(root: str, name: str) -> str | None:
    for base in (os.path.join(root, "images"), root):
        p = os.path.join(base, name)
        if os.path.isfile(p):
            return p
    return None


def check_digests(root: str, failures: list[str]) -> tuple[int, int]:
    xml_path = os.path.join(root, "md5sum.xml")
    if not os.path.isfile(xml_path):
        failures.append("md5sum.xml not found")
        return 0, 0
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as exc:
        failures.append(f"md5sum.xml is not valid XML: {exc}")
        return 0, 0

    ok = bad = 0
    for digest in tree.iter("digest"):
        name = digest.get("name")
        want = (digest.get("value") or digest.text or "").strip().lower()
        if not name or not want:
            failures.append("md5sum.xml has a digest without name or value")
            continue
        path = image_path(root, name)
        if not path:
            failures.append(f"missing image: {name}")
            bad += 1
            continue
        got = md5_file(path)
        if got == want:
            ok += 1
        else:
            failures.append(f"md5 mismatch: {name} (want {want}, got {got})")
            bad += 1
    return ok, bad


def check_scripts(root: str, device: str | None, anti: str | None,
                  failures: list[str]) -> None:
    flash = os.path.join(root, "flash_all.sh")
    if not os.path.isfile(flash):
        failures.append("flash_all.sh not found")
        return
    text = open(flash, "r", encoding="utf-8", errors="replace").read()

    product = None
    m = re.search(r"getvar\s+product[^\n]*product:\s*\*?([A-Za-z0-9_]+)", text)
    if m:
        product = m.group(1)
    else:
        m = re.search(r"getvar\s+product[^\n]*grep\s+\"\^?product:\s*\*?([A-Za-z0-9_]+)", text)
        if m:
            product = m.group(1)

    anti_ver = None
    m = re.search(r"^\s*CURRENT_ANTI_VER\s*=\s*(\d+)", text, re.MULTILINE)
    if m:
        anti_ver = m.group(1)

    print(f"flash_all.sh product check : {product or '(not found)'}")
    print(f"flash_all.sh CURRENT_ANTI_VER: {anti_ver or '(not found)'}")

    if product is None:
        failures.append("could not read the product check from flash_all.sh")
    elif device is not None and product != device:
        failures.append(f"device mismatch: ROM is for {product}, expected {device}")

    if anti_ver is None:
        failures.append("could not read CURRENT_ANTI_VER from flash_all.sh")
    elif anti is not None and anti_ver != str(anti):
        failures.append(f"anti mismatch: ROM wants {anti_ver}, phone has {anti}")

    if os.path.isfile(os.path.join(root, "flash_all_lock.sh")):
        print("WARNING: flash_all_lock.sh RELOCKS the bootloader - never run it.")


def main(argv: list[str]) -> int:
    rom = None
    device = None
    anti = None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            usage()
            return 0
        elif a == "--device":
            i += 1
            if i >= len(argv):
                print("check-rom: --device needs a codename", file=sys.stderr)
                return 2
            device = argv[i]
        elif a == "--anti":
            i += 1
            if i >= len(argv):
                print("check-rom: --anti needs a number", file=sys.stderr)
                return 2
            anti = argv[i]
        elif a.startswith("-"):
            print(f"check-rom: unknown option {a}", file=sys.stderr)
            return 2
        elif rom is None:
            rom = a
        else:
            print(f"check-rom: unexpected argument {a}", file=sys.stderr)
            return 2
        i += 1

    if rom is None:
        usage()
        return 2
    if not os.path.exists(rom):
        print(f"check-rom: {rom} does not exist", file=sys.stderr)
        return 2

    failures: list[str] = []
    tmp = None
    try:
        if os.path.isdir(rom):
            root = find_rom_root(rom)
        elif tarfile.is_tarfile(rom):
            prefix = archive_prefix(rom)
            print(f"archive: {os.path.basename(rom)}")
            got = md5_file(rom)
            print(f"archive MD5: {got}")
            if prefix is None:
                print("WARNING: the file name carries no hash prefix; skipping that check")
            elif got.startswith(prefix):
                print(f"archive hash prefix matches file name ({prefix})")
            else:
                failures.append(
                    f"archive MD5 {got} does not start with {prefix} from the file name")
            tmp = tempfile.mkdtemp(prefix="check-rom-")
            with tarfile.open(rom, "r:*") as tf:
                try:
                    tf.extractall(tmp, filter="data")
                except TypeError:
                    tf.extractall(tmp)
            root = find_rom_root(tmp)
        else:
            print(f"check-rom: {rom} is neither a folder nor a .tgz", file=sys.stderr)
            return 2

        print(f"ROM root: {root}")
        ok, bad = check_digests(root, failures)
        print(f"images verified: {ok} ok, {bad} bad")
        check_scripts(root, device, anti, failures)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)

    print()
    if failures:
        print(f"FAILED: {len(failures)} problem(s)")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK: every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
