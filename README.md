# FLAC Integrity Checker (FIC)

![Python 3.6+](https://img.shields.io/badge/python-3.6+-green.svg)
[![License](https://img.shields.io/badge/license-MIT-violet.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.4-orange.svg)](https://github.com/ryubic/reflac)

A robust, multi-threaded Python script to verify the integrity of FLAC audio files using `flac` and `metaflac`. It offers colored output, optional logging, smart error handling, file-type summaries, and runs in parallel for speed and efficiency.

---

## Features

- ✅ **Parallel Verification** — Uses ~75% of CPU threads for fast processing.
- ✅ **Checksum Validation** — Verifies embedded MD5 checksums with `metaflac`.
- ✅ **Cross-Platform** — Works on Windows, macOS, and Linux.
- ✅ **Progress Tracking** — Simple ASCII progress bar.
- ✅ **Detailed Logging** — Optional log file with timestamps.
- ✅ **File Summary** — Displays counts of audio, image, video, text, and archive files.
- ✅ **Read-Only** — Files are never modified.

---

## Requirements

- **Python 3.6+**
- `flac` and `metaflac` — [Download here](https://xiph.org/flac/download.html)
- Optional:
  - `tqdm` — For progress bar
  - `colorama` — For colored terminal output

---

## Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ryubic/reflac.git
   cd reflac
   ```

2. **Install optional dependencies**:
   ```bash
   pip install tqdm colorama 
   ```

3. **Ensure `flac` and `metaflac` are available**:
   ```bash
   flac -v
   metaflac 
   ```

---

## Usage

Run the script directly using Python:

```bash
python fic.py
```

### Examples:

- Scan a specific directory:
  ```bash
  python fic.py -d /path/to/music
  ```

- Create a log file:
  ```bash
  python fic.py -l
  ```

- Set thread count and timeout:
  ```bash
  python fic.py --max-threads 16 --timeout 20
  ```

### Command-Line Options:

- `-d, --directory` — Directory to scan (default: current directory)
- `-l, --log` — Save a detailed log file
- `-v` — Enable verbose output
- `--max-threads N` — Max number of parallel threads (default: 32)
- `--timeout S` — Timeout in seconds for verification (default: 30)
- `--max-retries N` — Retries for checksum checks (default: 2)

---

## Output

- ✅ **Passed** — File is valid and MD5 matches
- ❌ **Failed** — File is corrupt or unreadable
- ⚠️ **No MD5** — Missing or zeroed-out MD5 field

Also includes:
- A table of file types found (audio, image, video, etc.)
- A verification summary
- Optionally, a timestamped log file (e.g., `flac_check_20250601_153045.log`)

---

## Troubleshooting

**Missing `flac` or `metaflac`?**

### Linux:
```bash
sudo apt install flac      # Debian/Ubuntu
sudo pacman -S flac        # Arch
sudo dnf install flac      # Fedora
```

### macOS:
```bash
brew install flac
```

### Windows:
1. Download from [xiph.org](https://xiph.org/flac/download.html)
2. Add to your system PATH, or place `flac.exe` and `metaflac.exe` in the same directory as `fic.py`

---

## Notes

- Files are scanned and verified in a read-only manner.
- The script handles symbolic links and inaccessible files gracefully.
- The log file contains detailed messages including exceptions (if verbose mode is enabled).

---

## License

This project is licensed under the MIT License.

---