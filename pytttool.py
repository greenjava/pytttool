import argparse
import os
import sys

# ---- Constants for the GME file format ----
VERSION_OFFSET = 0x20
HEADER_SIZE = 0x64
LANG_BLOCK_END = 0x60
DATE_FIELD_LENGTH = 8
CHECKSUM_LENGTH = 4
PRODUCT_ID_OFFSET = 0x00
PRODUCT_ID_SIZE = 2  # uint16_t, little endian

ALLOWED_LANGUAGES = {"GERMAN", "DUTCH", "FRENCH", "ITALIA", "RUSSIA", "ENGLISH"}


def print_gme_info(filepath):
    """Print general info about a GME file (extended fields)."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File '{filepath}' does not exist.")
    with open(filepath, "rb") as f:
        buffer = bytearray(f.read())
    if len(buffer) < HEADER_SIZE:
        raise ValueError("Input file is too short to be a valid GME file.")
    # Product ID
    product_id = buffer[0] + (buffer[1] << 8)
    # Raw XOR value (uint32_le at 0x0C)
    raw_xor = buffer[0x0C] + (buffer[0x0D] << 8) + (buffer[0x0E] << 16) + (buffer[0x0F] << 24)
    # Magic XOR value (byte at 0x12)
    magic_xor = buffer[0x12]
    # Comment: null-terminated string from 0x1C (max 32 bytes)
    comment_bytes = buffer[0x1C:0x3C]
    comment = comment_bytes.split(b'\x00')[0].decode(errors="replace")
    # Version string length at 0x20, string at 0x21
    version_len = buffer[VERSION_OFFSET]
    version_bytes = buffer[VERSION_OFFSET + 1: VERSION_OFFSET + 1 + version_len]
    version = version_bytes.decode(errors="replace")
    # Date (8 ASCII digits) follows version string, if present
    date = ""
    lang_pos = VERSION_OFFSET + 1 + version_len
    if lang_pos + 8 <= len(buffer) and all(chr(buffer[lang_pos + i]).isdigit() for i in range(8)):
        date = "".join(chr(buffer[lang_pos + i]) for i in range(8))
        lang_pos += 8
    # Language
    if LANG_BLOCK_END < lang_pos:
        language = ""
    else:
        lang_max_len = LANG_BLOCK_END - lang_pos
        lang_bytes = buffer[lang_pos:lang_pos + lang_max_len]
        language = lang_bytes.split(b'\x00', 1)[0].decode(errors="replace")
    # Checksum
    checksum_found = buffer[-4] + (buffer[-3] << 8) + (buffer[-2] << 16) + (buffer[-1] << 24)
    checksum_calc = sum(buffer[:-4]) & 0xFFFFFFFF

    print(f"GME file: {filepath}")
    print(f"  Product ID           : {product_id}")
    print(f"  Raw XOR value        : 0x{raw_xor:08X}")
    print(f"  Magic XOR value      : 0x{magic_xor:02X}")
    print(f"  Comment              : {comment}")
    print(f"  Version              : {version}")
    if date:
        print(f"  Date                 : {date}")
    print(f"  Language             : {language if language else '(not set)'}")
    print(f"  Checksum found       : 0x{checksum_found:08X}")
    if checksum_found == checksum_calc:
        print(f"  Checksum calculated  : 0x{checksum_calc:08X} (OK)")
    else:
        print(f"  Checksum calculated  : 0x{checksum_calc:08X} (DIFFERENT)")
    print(f"  File size            : {len(buffer)} bytes")
    # The rest ("Number of registers", "Initial registers", etc) requires GME-specific further parsing


def update_gme_checksum(buffer):
    """Compute and update the checksum in the last 4 bytes of the buffer."""
    if len(buffer) < CHECKSUM_LENGTH:
        raise ValueError("File too small for checksum.")
    checksum = sum(buffer[:-CHECKSUM_LENGTH]) & 0xFFFFFFFF
    cs_offset = len(buffer) - CHECKSUM_LENGTH
    buffer[cs_offset] = (checksum) & 0xFF
    buffer[cs_offset + 1] = (checksum >> 8) & 0xFF
    buffer[cs_offset + 2] = (checksum >> 16) & 0xFF
    buffer[cs_offset + 3] = (checksum >> 24) & 0xFF


def write_buffer_to_file(filepath, buffer):
    """Write the buffer to a temp file and replace the original atomically."""
    tmpfile = filepath + ".tmp"
    with open(tmpfile, "wb") as f:
        f.write(buffer)
    os.replace(tmpfile, filepath)


def set_gme_language(filepath, language):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File '{filepath}' does not exist.")
    if language.upper() not in ALLOWED_LANGUAGES:
        raise ValueError(
            f"Invalid language '{language}'. "
            f"Allowed languages: {', '.join(sorted(ALLOWED_LANGUAGES))}"
        )
    with open(filepath, "rb") as f:
        buffer = bytearray(f.read())
    if len(buffer) < HEADER_SIZE:
        raise ValueError("Input file is too short to be a valid GME file.")
    version_len = buffer[VERSION_OFFSET]
    lang_pos = VERSION_OFFSET + 1 + version_len
    has_date = lang_pos < len(buffer) and chr(buffer[lang_pos]).isdigit()
    if has_date:
        lang_pos += DATE_FIELD_LENGTH
    if LANG_BLOCK_END <= lang_pos:
        raise ValueError("GME file layout invalid: language offset past block end.")
    lang_max_len = LANG_BLOCK_END - lang_pos
    lang_to_write = language[:lang_max_len]
    if len(language) > lang_max_len:
        print(f"Warning: Language string too long, truncated to {lang_to_write}")
    for i in range(lang_max_len):
        buffer[lang_pos + i] = ord(lang_to_write[i]) if i < len(lang_to_write) else 0x00
    update_gme_checksum(buffer)
    write_buffer_to_file(filepath, buffer)


def set_gme_product_id(filepath, product_id):
    """Set the product id field of a GME file, update the checksum, and save in place."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"File '{filepath}' does not exist.")
    if not (0 <= product_id < 65536):
        raise ValueError("Product ID must be in range 0–65535.")
    with open(filepath, "rb") as f:
        buffer = bytearray(f.read())
    if len(buffer) < HEADER_SIZE:
        raise ValueError("Input file is too short to be a valid GME file.")
    # Write Product ID as little-endian uint16 at offset 0x00
    buffer[PRODUCT_ID_OFFSET] = product_id & 0xFF
    buffer[PRODUCT_ID_OFFSET + 1] = (product_id >> 8) & 0xFF
    update_gme_checksum(buffer)
    write_buffer_to_file(filepath, buffer)


def main():
    parser = argparse.ArgumentParser(
        description="GME file modification utility (set-language, set-product-id, ...)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # set-language command
    lang_parser = subparsers.add_parser(
        'set-language',
        help="Sets the language field of a GME file",
        description="Sets the language field of a GME file"
    )
    lang_parser.add_argument(
        'language',
        help=f"Language ({', '.join(sorted(ALLOWED_LANGUAGES))})"
    )
    lang_parser.add_argument(
        'gmefile',
        help="GME file to modify"
    )

    # set-product-id command
    id_parser = subparsers.add_parser(
        'set-product-id',
        help="Changes the product id of a GME file",
        description="Changes the product id of a GME file"
    )
    id_parser.add_argument(
        'product_id',
        type=int,
        help="Product id (integer, typically < 1000)"
    )
    id_parser.add_argument(
        'gmefile',
        help="GME file to modify"
    )

    # info command
    info_parser = subparsers.add_parser(
        'info',
        help="Print general information about a GME file",
        description="Print general information about a GME file"
    )
    info_parser.add_argument(
        'gmefile',
        help="GME file to analyze"
    )
    args = parser.parse_args()

    if args.command == "set-language":
        try:
            set_gme_language(args.gmefile, args.language)
            print(f"Language updated to '{args.language}' successfully.")
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            sys.exit(1)
    elif args.command == "set-product-id":
        try:
            set_gme_product_id(args.gmefile, args.product_id)
            print(f"Product ID updated to '{args.product_id}' successfully.")
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            sys.exit(1)
    elif args.command == "info":
        try:
            print_gme_info(args.gmefile)
        except Exception as e:
            print("Error:", e, file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
