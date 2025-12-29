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


if __name__ == "__main__":
    main()
