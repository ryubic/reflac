# FLAC Integrity Checker (fic.py)

A robust, multi-threaded Python script to verify the integrity of FLAC audio files using `flac` and `metaflac`. It offers colored output, optional logging, smart error handling, file-type summaries, and runs in parallel for speed and efficiency.

## Features 

- **Parallel Verification** — Uses ~75% of CPU threads for fast processing.
- **Checksum Validation** — Verifies embedded MD5 checksums with `metaflac`.
- **Cross-Platform** — Works on Windows, macOS, and Linux.
- **Progress Tracking** — Simple ASCII progress bar.
- **Detailed Logging** — Optional log file with timestamps.
- **File Summary** — Displays counts of audio, image, video, text, and archive files.
- **Read-Only** — Files are never modified.

## Requirements

- **Python 3.6+**
- `flac` and `metaflac` — [Download here](https://xiph.org/flac/download.html)
- Optional:
  - `tqdm` — For progress bar
  - `colorama` — For colored terminal output

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

## Output

- **Passed** — File is valid and MD5 matches
- **Failed** — File is corrupt or unreadable
- **No MD5** — Missing or zeroed-out MD5 field

Also includes:
- A table of file types found (audio, image, video, etc.)
- A verification summary
- Optionally, a timestamped log file (e.g., `flac_check_20250601_153045.log`)

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

# FLAC Recompressor / fix unset MD5 (recompress.py)

A Python script to recompress FLAC audio files in a specified directory using the FLAC command-line tool. It processes files in parallel with a configurable compression level and provides a progress bar with success/failure tracking.

## Features

- **Parallel Processing**: Utilizes 75% of available CPU threads for efficient re-encoding.
- **Configurable Compression**: Supports FLAC compression levels from 0 (fastest) to 8 (highest compression), defaulting to 5.
- **Progress Tracking**: Displays a real-time progress bar with percentage, processed files, and success/failure counts.
- **Error Reporting**: Lists detailed errors with full file paths for any failed re-encodings.
- **User Confirmation**: Prompts for confirmation before starting, showing the directory, file count, compression level, and thread count.
- **Cross-Platform**: Works on Windows, macOS, and Linux with proper path handling.

## Prerequisites

- **Python 3.6+**: Required to run the script.
- **FLAC**: The FLAC command-line tool must be installed and available in your system PATH.
  - On Windows: Download from [Xiph.org](https://xiph.org/flac/download.html).
  - On Linux: Install via your package manager (e.g., `sudo apt install flac` on Ubuntu).
- **Colorama**: Python library for colored terminal output (`pip install colorama`).

## Installation

1. Clone or download this repository:
   ```bash
   git clone https://github.com/ryubic/reflac
   cd reflac
   ```
2. Install the required Python dependency:
   ```bash
   pip install colorama
   ```
3. Ensure `flac` is installed and accessible:
   ```bash
   flac --version
   ```
   If this fails, install FLAC as per your operating system instructions above.

## Usage

Run the script from the command line with optional arguments:

### Basic Usage
Recompress FLAC files in the current directory with default compression level (5):
```bash
python recompress.py
```

### Specify Directory and Compression Level
Recompress FLAC files in a specific directory with a custom compression level (e.g., 8):
```bash
python recompress.py -d /path/to/music -c 8
```

### Command-Line Options
- `-d, --directory`: Directory to search for FLAC files (default: current directory).
- `-c, --compression`: Compression level from 0 to 8 (default: 5).

## Notes

- **Thread Usage**: The script uses 75% of available CPU threads to balance performance and system responsiveness.
- **Error Handling**: If FLAC is not installed or files fail to process, detailed errors are shown with full paths.
- **Confirmation**: Press 'Y' or Enter to start; any other input aborts the process.

---

## Contributing

Feel free to submit issues or pull requests:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.
