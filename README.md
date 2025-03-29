# FLAC Integrity Checker (FIC)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
![Python 3.6+](https://img.shields.io/badge/python-3.6+-green.svg)
![Version 1.2.0](https://img.shields.io/badge/version-1.2.0-orange)

A robust tool for verifying FLAC file integrity with parallel processing, comprehensive error reporting, and logging capabilities.

## Features

- Parallel processing for efficient verification of large music collections
- Comprehensive error detection and reporting
- MD5 checksum verification
- Colorized console output (when supported)
- Detailed logging functionality
- Progress bar visualization (with tqdm)
- Robust error handling and recovery mechanisms
- Read-only file operations for data safety

## Requirements

- Python 3.6 or higher
- FLAC command-line tools:
  - `flac` - FLAC encoder/decoder
  - `metaflac` - FLAC metadata editor/viewer

Optional dependencies:
- `colorama` - For colorized terminal output
- `tqdm` - For progress bar display

## Installation

1. Clone this repository:
```bash
git clone https://github.com/rubic-codes/FLAC-Integrity-Checker.git
cd FLAC-Integrity-Checker
```

2. Install optional Python dependencies:
```bash
pip install colorama tqdm
```

3. Ensure FLAC tools are installed on your system:
   - **Linux**: `sudo apt-get install flac` (or equivalent for your distribution)
   - **macOS**: `brew install flac`
   - **Windows**: Download from [FLAC official website](https://xiph.org/flac/download.html) and add to PATH

## Usage

### Basic Usage

```bash
# Scan current directory
python FIC.py

# Scan specific directory
python FIC.py -d /path/to/music/collection

# Create a log file during scan
python FIC.py -l

# Scan specific directory and create log
python FIC.py -d /path/to/music/collection -l

# Enable verbose output
python FIC.py -v
```

### Command-line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `-d`, `--directory` | Directory to scan | Current directory |
| `-l`, `--log` | Create a log file | Disabled |
| `-v`, `--verbose` | Enable verbose output | Disabled |
| `--version` | Show version information | - |

## Output

The tool provides a comprehensive summary of verification results:

- Total files checked
- Files that passed verification
- Files that failed verification (with error details)
- Files without MD5 checksums
- Log file path (if created)

Example output:
```
==================================================================================
                         FLAC INTEGRITY CHECKER v1.2.0                         
                 Verify the integrity of your FLAC audio files                 
==================================================================================

Target directory: /path/to/music
Searching for FLAC files...
Found 1532 FLAC files
Starting verification using 6 threads...
[████████████████████████████████████] 1532/1532 [02:14<00:00]

Verification Complete
-------------------------- Verification Summary ---------------------------
Total files checked: 1532
Passed verification: 1527
Failed verification: 3
Files without MD5: 2
Log file created: flac_check_20250329_123456.log
------------------------------------------------------------------------
Failed files:
1. /path/to/music/album/corrupted_track.flac
   ERROR: md5sum mismatch in frame -12 expected: eb5dca41142c9ebcc75ea994ac5d3215
2. /path/to/music/album2/bad_file.flac
   File inaccessible or unreadable
3. /path/to/music/album3/broken_metadata.flac
   ERROR: invalid metadata
------------------------------------------------------------------------
Files without MD5 checksums:
1. /path/to/music/old_album/track01.flac
2. /path/to/music/old_album/track02.flac
------------------------------------------------------------------------
```

## Error Codes

The program exits with the following status codes:
- `0`: All files passed verification or no files found
- `1`: One or more files failed verification, dependency check failed, or program error

## Logging

When enabled with the `-l` flag, the program creates a timestamped log file that includes:
- Program start and configuration details
- File discovery information
- Verification results for each file
- Error details and stack traces (in debug mode)
- Final summary

## Advanced Configuration

The following environment variables can be set:
- `DEBUG_FLAC_CHECKER=1` - Enable detailed error tracebacks in logs

## How It Works

1. Searches recursively for `.flac` files in the specified directory
2. Utilizes multiple threads for parallel processing
3. For each file:
   - Performs accessibility checks
   - Runs `flac -t` for integrity verification (read-only)
   - Uses `metaflac --show-md5sum` to verify internal MD5 checksums
4. Collects results and generates comprehensive reports

## Troubleshooting

- **Missing dependencies**: Ensure `flac` and `metaflac` are installed and in your PATH
- **Permission errors**: Ensure you have read access to the files and directories
- **Slow performance**: Consider optimizing thread count based on your system
- **Out of memory**: For extremely large collections, scan subdirectories separately

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request to the [FLAC Integrity Checker repository](https://github.com/rubic-codes/FLAC-Integrity-Checker).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The FLAC project for their excellent audio codec and tools
- All contributors and testers who have provided feedback
