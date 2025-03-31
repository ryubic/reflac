# FLAC Integrity Checker

![Python 3.6+](https://img.shields.io/badge/python-3.6+-green.svg)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.2.1-blue.svg)](https://github.com/rubic-codes/FLAC-Integrity-Checker)

A robust command-line tool for verifying the integrity of FLAC audio files with parallel processing, comprehensive error reporting, and logging capabilities.

## Features

- **Thorough FLAC verification**: Tests the integrity of FLAC files using the official FLAC tools
- **MD5 checksum validation**: Verifies embedded MD5 checksums in FLAC files
- **Multi-threaded processing**: Automatically utilizes multiple CPU cores for faster verification
- **Detailed reporting**: Provides comprehensive results including detailed error messages
- **Color-coded output**: Uses color to highlight important information (when supported)
- **Progress tracking**: Shows real-time progress during verification process
- **Logging support**: Optional logging to file for record-keeping
- **File statistics**: Displays breakdown of file types found during scan
- **Safe read-only operations**: Never modifies your audio files
- **Robust error handling**: Includes retries for transient errors and comprehensive error reporting

## Installation

### Prerequisites

This tool requires Python 3.6 or later and the FLAC command-line tools:

- `flac`: The official FLAC encoder/decoder
- `metaflac`: FLAC metadata editor

#### Installing FLAC tools

**Windows:**
- Download the FLAC tools from https://xiph.org/flac/download.html
- Add the installation directory to your PATH environment variable

**macOS:**
```bash
brew install flac
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install flac

# Fedora
sudo dnf install flac

# Arch Linux
sudo pacman -S flac
```

### Installing the Script

1. Clone the repository or download the script:
   ```bash
   git clone https://github.com/rubic-codes/FLAC-Integrity-Checker.git
   cd FLAC-Integrity-Checker
   ```

2. Make it executable (Linux/macOS):
   ```bash
   chmod +x FIC.py
   ```

3. Optional: Install the progress bar library for better output:
   ```bash
   pip install tqdm
   ```

4. Optional: Install colorama for colored output on Windows:
   ```bash
   pip install colorama
   ```

## Usage

### Basic Usage

```bash
python FIC.py
```
This will scan the current directory and all subdirectories for FLAC files.

### Scan a Specific Directory

```bash
python FIC.py -d "/path/to/music collection"
```

### Create a Log File

```bash
python FIC.py -l
```

### Verbose Output with Logging

```bash
python FIC.py -d "/path/to/music" -l -v
```

### Command-line Options

```
usage: FIC.py [-h] [-d DIRECTORY] [-l] [-v] [--version]

FLAC Integrity Checker  - Verify the integrity of FLAC audio files

optional arguments:
  -h, --help            show this help message and exit
  -d DIRECTORY, --directory DIRECTORY
                        Directory to scan (default: current directory)
  -l, --log             Create a log file of the verification process
  -v, --verbose         Enable verbose output
  --version             show program's version number and exit
```

## Understanding the Results

The tool provides a detailed summary after scanning:

- **Passed verification**: Files that passed both FLAC structure and MD5 checksum verification
- **Failed verification**: Files with structural errors or corrupted data
- **Files without MD5**: Files that are structurally valid but don't have an MD5 checksum embedded

### Example Output

```
===============================================================================
                       FLAC INTEGRITY CHECKER v1.2.1                        
                Verify the integrity of your FLAC audio files                
===============================================================================

Target directory: /path/to/music
Searching for files...

---------------- Files Found ----------------
Audio:
  flac: 1250     mp3: 84        wav: 12       
  m4a: 5         

Images:
  jpg: 145       png: 28        

Text/Docs:
  txt: 15        log: 8         cue: 5        

Archives:
  zip: 2         

Other:
  Other files: 7
------------------------------------------
Total files: 1561
------------------------------------------

Starting verification of 1250 FLAC files
Using 12 threads for verification...
[████████████████████████████████████████] 1250/1250 [00:43<00:00]

Verification Complete

---------------- Verification Summary ----------------
Total files checked: 1250
Passed verification: 1247
Failed verification: 2
Files without MD5: 1
Log file created: flac_check_20250331_123045.log
--------------------------------------------------
Failed files:
1. /path/to/music/Album/Track01.flac
   stream decoder error: CRC mismatch
2. /path/to/music/Compilation/Track05.flac
   stream decoder error: unexpected EOF
--------------------------------------------------
Files without MD5 checksums:
1. /path/to/music/Recently Added/NewAlbum/Track02.flac
--------------------------------------------------
```

## Interpreting Errors

Common error messages and their meanings:

1. **CRC mismatch**: Data corruption has occurred, the file's CRC checksum doesn't match the calculated value
2. **Unexpected EOF**: The file is truncated or incomplete
3. **Wrong sync code**: The file structure is damaged, possibly due to disk errors or incomplete downloads
4. **Metadata failure**: The metadata blocks are corrupted
5. **File inaccessible or unreadable**: Permission issues or file system problems

## Exit Codes

The program returns the following exit codes:

- `0`: All files passed verification (or no FLAC files were found)
- `1`: One or more files failed verification or the program encountered an error

## Troubleshooting

### Missing Dependencies

If you receive an error about missing commands:

```
Error: The following tools are required but not found:
  • flac
  • metaflac
```

Make sure you have installed the FLAC tools as described in the Prerequisites section.

### Permission Issues

If files fail with "File inaccessible or unreadable" errors:
- Ensure you have read permissions for the files and directories
- Try running the script with elevated privileges if necessary

### Path Issues on Windows

If you encounter problems with paths containing spaces on Windows:
- Make sure to use double quotes around the directory path:
  ```
  python FIC.py -d "C:\My Music Collection"
  ```

## Advanced Usage

### Environment Variables

- `DEBUG_FLAC_CHECKER`: Set this environment variable to any value to include stack traces in error logs

### Integration with Other Tools

The exit code can be used to integrate with other scripts or notification systems:

```bash
python FIC.py && echo "All files verified successfully" || echo "Some files failed verification"
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request on the [GitHub repository](https://github.com/rubic-codes/FLAC-Integrity-Checker).

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- The FLAC project for their excellent audio codec and tools
- All contributors and testers who have provided feedback
