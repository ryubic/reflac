# FLAC Integrity Checker

## Overview
FLAC Integrity Checker is a robust and efficient tool for verifying the integrity of FLAC files. It supports parallel processing, detailed error reporting, and MD5 checksum verification to ensure the accuracy of your FLAC files.

## Features
- **Parallel Processing**: Uses multiple threads to speed up verification.
- **FLAC Verification**: Uses `flac -t` to check file integrity.
- **MD5 Checksum Verification**: Ensures file consistency via `metaflac --show-md5sum`.
- **Error Handling**: Provides detailed error messages for failed files.
- **Progress Indicator**: Supports `tqdm` for progress tracking (optional).
- **Cross-platform Compatibility**: Works on Linux, macOS, and Windows.

## Requirements
Ensure the following dependencies are installed:
- Python 3.6+
- `flac` (command-line tool)
- `metaflac` (metadata tool for FLAC files)
- `tqdm` (optional, for progress display)

### Installation of Dependencies
On Linux:
```sh
sudo apt install flac  # Debian-based
sudo dnf install flac  # Fedora-based
```
On macOS:
```sh
brew install flac
```
On Windows:
Ensure `flac.exe` and `metaflac.exe` are in your system's `PATH`.

To install `tqdm` for progress tracking:
```sh
pip install tqdm
```

## Usage
To run the FLAC Integrity Checker in the current directory:
```sh
python FIC.py
```

### Options
- **Environment Variables:**
  - `DEBUG_FLAC_CHECKER=1` Enables detailed error traceback.

## How It Works
1. **File Discovery**: Scans for FLAC files in the specified directory.
2. **Accessibility Check**: Ensures files are readable and valid.
3. **FLAC Verification**: Runs `flac -t` to check file integrity.
4. **MD5 Verification**: Uses `metaflac --show-md5sum` to validate checksums.
5. **Parallel Processing**: Uses multiple threads for efficiency.
6. **Results Summary**: Displays passed, failed, and missing MD5 checksum files.

## Example Output
```
FLAC INTEGRITY CHECKER
----------------------
Searching for FLAC files...
Found 120 files.
Starting verification using 8 threads...

Verification Summary
----------------------
Total files checked: 120
Passed verification: 115
Failed verification: 3
Files without MD5: 2

Failed files:
1. /music/album1/track3.flac
   ERROR: Corrupt FLAC stream
2. /music/album2/track7.flac
   ERROR: Read error
```

## Troubleshooting
- **Command Not Found:** Ensure `flac` and `metaflac` are installed and in your `PATH`.
- **Permission Errors:** Run with appropriate file permissions.
- **False Negatives:** Try increasing `MAX_RETRIES` in the script.

## License
This project is open-source and released under the MIT License.

## Contributions
Feel free to submit pull requests or report issues to improve the tool!

