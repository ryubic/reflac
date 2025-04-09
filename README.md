# FLAC Integrity Checker

![Python 3.6+](https://img.shields.io/badge/python-3.6+-green.svg)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.2.1-orange.svg)](https://github.com/rubic-codes/FLAC-Integrity-Checker)

A robust, multi-threaded tool to verify the integrity of FLAC audio files using `flac` and `metaflac`. It offers smart error handling, colored output, detailed logging, dependency checks, and file statistics — all with a focus on speed and accuracy.

---

## Features

- Parallel verification of FLAC files
- Checks embedded MD5 checksums
- Summarizes other file types in directory
- Logs optional detailed reports
- Cross-platform (Linux, macOS, Windows)
- Colored terminal output (optional)

---

## Requirements

- Python 3.7+
- [flac](https://xiph.org/flac/download.html)
- [metaflac](https://xiph.org/flac/download.html)

Optional:
- `colorama` for colored output
- `tqdm` for a progress bar

---

## Installation

1. **Clone this repo**:
```bash
git clone https://github.com/rubic-codes/FLAC-Integrity-Checker.git
cd FLAC-Integrity-Checker
```

2. **(Optional) Install extras**:
```bash
pip install colorama tqdm
```

---

## Usage

Basic usage:
```bash
python FIC.py
```

Scan specific directory:
```bash
python FIC.py -d /path/to/music
```

Create a log file:
```bash
python FIC.py -l
```

Other options:
- `--max-threads N` — Set max threads (default: 32)
- `--timeout S` — Set timeout for FLAC validation (default: 30s)
- `--max-retries N` — Retry metaflac checks (default: 2)
- `-v` — Enable verbose logging

Example:
```bash
python FIC.py -d "." -l --max-threads 16 --timeout 20
```

---

## Output

- **Passed**: FLAC file is valid with matching MD5
- **Failed**: FLAC test or MD5 check failed
- **No MD5**: MD5 field is missing or empty

You’ll also get:
- A file type summary (audio, images, video, etc.)
- A summary of verification results
- Optional log file: `flac_check_YYYYMMDD_HHMMSS.log`

---

## Troubleshooting

**Missing `flac` or `metaflac`?**

- **Linux**:
```bash
sudo apt install flac      # Debian/Ubuntu
sudo pacman -S flac        # Arch
sudo dnf install flac      # Fedora
```

- **macOS**:
```bash
brew install flac
```

- **Windows**:
Download from [xiph.org](https://xiph.org/flac/download.html), then:
- Add to your PATH, or
- Place the executables in the same folder as `FIC.py`

---

## License

This project is licensed under the MIT License.

---

## Contributing

PRs and suggestions welcome! If you find a bug or want to improve performance or formatting, feel free to open an issue or submit a PR.

---

## Version

**v1.2.2** — See `FIC.py` for the full changelog.

---

## Disclaimer

This script does not modify any files. It is designed for **read-only** operations.
