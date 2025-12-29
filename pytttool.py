import os
import sys

# ---- Constants for the GME file format ----
VERSION_OFFSET = 0x20
HEADER_SIZE = 0x64
LANG_BLOCK_END = 0x60
DATE_FIELD_LENGTH = 8
CHECKSUM_LENGTH = 4

# ---- Allowed languages ----
ALLOWED_LANGUAGES = {"GERMAN", "DUTCH", "FRENCH", "ITALIA", "RUSSIA", "ENGLISH"}


def set_gme_language(filepath, language):
    """Set the language field of a GME file, update the checksum, and save in place."""

    if language.upper() not in ALLOWED_LANGUAGES:
        raise ValueError(
            f"Invalid language '{language}'. "
            f"Allowed languages: {', '.join(sorted(ALLOWED_LANGUAGES))}"
        )

    # Read file into a mutable bytearray
    with open(filepath, "rb") as f:
        buffer = bytearray(f.read())
    if len(buffer) < HEADER_SIZE:
        raise ValueError("Input file is too short to be a valid GME file.")

    version_len = buffer[VERSION_OFFSET]
    lang_pos = VERSION_OFFSET + 1 + version_len
    # Check for extra date field (first char after version is a digit)
    has_date = lang_pos < len(buffer) and chr(buffer[lang_pos]).isdigit()
    if has_date:
        lang_pos += DATE_FIELD_LENGTH

    if LANG_BLOCK_END <= lang_pos:
        raise ValueError("GME file layout invalid: language offset past block end.")

    lang_max_len = LANG_BLOCK_END - lang_pos
    lang_to_write = language[:lang_max_len]
    if len(language) > lang_max_len:
        print(f"Warning: Language string too long, truncated to {lang_to_write}")

    # Write new language string and zero-pad if needed
    for i in range(lang_max_len):
        buffer[lang_pos + i] = ord(lang_to_write[i]) if i < len(lang_to_write) else 0x00

    # Compute checksum of all bytes except for the last 4 bytes
    if len(buffer) < CHECKSUM_LENGTH:
        raise ValueError("File too small for checksum.")
    checksum = sum(buffer[:-CHECKSUM_LENGTH]) & 0xFFFFFFFF
    # Write checksum in little-endian at the end
    cs_offset = len(buffer) - CHECKSUM_LENGTH
    buffer[cs_offset] = (checksum) & 0xFF
    buffer[cs_offset + 1] = (checksum >> 8) & 0xFF
    buffer[cs_offset + 2] = (checksum >> 16) & 0xFF
    buffer[cs_offset + 3] = (checksum >> 24) & 0xFF

    # Save to temp file and atomically replace the original
    tmpfile = filepath + ".tmp"
    with open(tmpfile, "wb") as f:
        f.write(buffer)
    os.replace(tmpfile, filepath)


# Example usage (uncomment for standalone use)
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} myfile.gme LANGUAGE")
        print(f"Allowed languages: {', '.join(sorted(ALLOWED_LANGUAGES))}")
        sys.exit(1)
    try:
        set_gme_language(sys.argv[1], sys.argv[2])
        print("Language updated successfully.")
    except Exception as e:
        print("Error:", e, file=sys.stderr)
        sys.exit(1)
