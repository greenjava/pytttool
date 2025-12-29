# pytttool: GME File Modification Tool

This Python program allows you to modify the contents
of [GME](https://github.com/entropia/tip-toi-reveng/blob/master/GME-Format.md) files, which are used by the Ravensburger
Tiptoi system.  
It currently supports the following modification commands, similar to the `tttool` utility:

- **GME modification commands:**
    - `set-language` set the language field of a GME file (restricted to known values)
    - `set-product-id` change the product ID of a GME file
- **GME analysis commands:**
    - `info` print general information about a GME file (product ID, language, version, etc.)

The script also ensures that the internal file checksum is correctly updated after any modification.

---

## Features

- **Set the language field:**  
  Only the following languages are allowed (case-insensitive):  
  `GERMAN`, `DUTCH`, `FRENCH`, `ITALIA`, `RUSSIA`, `ENGLISH`.
- **Change the product ID:**  
  The product ID must be an integer between 0 and 65535 (typically below 1000).
- **Show general information:**  
  The `info` command prints product ID, language, version, comment, XOR and checksum, and other key details for
  inspection.
- **Atomic file update:**  
  Changes are written to a temporary file and then replace the original, ensuring data integrity.
- **Checksum handling:**  
  The file's final checksum is recalculated and updated automatically after any modification.
- **Subcommand structure:**  
  The script is designed for extensibility. Additional modification commands can be added easily.

---

## Usage

```sh
python mytool.py set-language LANGUAGE FILE.gme
python mytool.py set-product-id PRODUCT_ID FILE.gme
python mytool.py info FILE.gme
```

### Parameters

- `LANGUAGE`: One of the allowed language codes (`GERMAN`, `DUTCH`, `FRENCH`, `ITALIA`, `RUSSIA`, `ENGLISH`)
- `FILE.gme`: The path to the GME file you wish to modify.
- `PRODUCT_ID`: An integer value (e.g. 1234).

### Examples

```sh
python mytool.py set-language FRENCH WWW_Bauernhof.gme
python mytool.py set-product-id 991 WWW_Bauernhof.gme
python mytool.py info WWW_Bauernhof.gme
```

---

## Example Output (info command)

```
GME file: WWW_Bauernhof.gme
  Product ID           : 48
  Raw XOR value        : 0x000000D0
  Magic XOR value      : 0x1D
  Comment              : CHOMPTECH DATA FORMAT CopyRight 2009 Ver2.10.0901
  Version              : 2.10.0901
  Date                 : 20141029
  Language             : GERMAN
  Checksum found       : 0x4769ECF9
  Checksum calculated  : 0x4769ECF9 (OK)
  File size            : 294912 bytes
```

---

## Requirements

- Python 3.6 or higher
- No external dependencies (only Python standard library)

---

## Notes

- The script checks the file format and validates parameters. Files that are too short or use an invalid language or
  product id will result in an error.
- All changes update the GME file in-place, after atomic write to a temporary file for safety.
- The code is structured so you can easily add new commands (subparsers in `argparse`).

---

## License

This script is released under the MIT License.  
It is inspired by the functionality of the [tttool](https://github.com/entropia/tip-toi-reveng) project.

---