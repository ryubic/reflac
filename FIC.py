#!/usr/bin/env python3
"""
FLAC Integrity Checker - A robust tool for verifying FLAC file integrity
with parallel processing, comprehensive error reporting, and logging capabilities.

Usage:
  - To scan current directory: python FICv3.py
  - To scan specific directory: python FICv3.py -d /path/to/directory
  - To create a log file: python FICv3.py -l
  - To scan specific directory and create log: python FICv3.py -d /path/to/directory -l
"""

import argparse
import concurrent.futures
import datetime
import logging
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# Constants
VERSION = "1.2.1"
MAX_THREADS = 32  # Safety limit for maximum threads
MAX_RETRIES = 2  # Number of retries for failed operations
FILE_READ_CHUNK = 8192  # Chunk size for file reading checks
FLAC_VERIFY_TIMEOUT = 30  # Seconds for FLAC verification timeout
MD5_CHECK_TIMEOUT = 10  # Seconds for MD5 check timeout

# Color setup
class Colors:
    """Color definitions and formatter"""
    def __init__(self):
        self.enabled = False
        self._init_colors()

    def _init_colors(self):
        try:
            from colorama import init, Style
            init()
            self.enabled = True
            self.orange_red = '\033[38;5;202m'  # Error color
            self.yellow = '\033[38;5;185m'      # Warning color (no MD5)
            self.green = '\033[92m'             # Success color
            self.purple = '\033[38;5;147m'      # Info/header color
            self.reset = Style.RESET_ALL
        except ImportError:
            self.enabled = False
            self.orange_red = self.yellow = self.green = self.purple = self.reset = ''

    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if enabled"""
        if not self.enabled:
            return text
        color_code = getattr(self, color, '')
        return f"{color_code}{text}{self.reset}"

colors = Colors()

class VerificationResult(NamedTuple):
    """Container for verification results"""
    file_path: str
    status: str  # 'passed', 'failed', or 'no_md5'
    error: Optional[str]
    md5sum: Optional[str] = None

def setup_logging(enable_logging: bool) -> Optional[str]:
    """Configure logging to file if enabled"""
    if not enable_logging:
        return None
        
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"flac_check_{timestamp}.log"
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Add console handler for ERROR level and above
    console = logging.StreamHandler()
    console.setLevel(logging.ERROR)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    
    logging.info(f"FLAC Integrity Checker v{VERSION} started")
    return log_filename

def get_optimal_threads() -> int:
    """Calculate optimal number of threads with safety limits."""
    try:
        cpu_count = multiprocessing.cpu_count()
        # Use 75% of cores with min 1, max MAX_THREADS
        return min(MAX_THREADS, max(1, int(cpu_count * 0.75)))
    except (NotImplementedError, ImportError):
        return 1  # Fallback to single thread if detection fails

def clean_flac_error(error: str) -> str:
    """Clean up FLAC error messages."""
    if not error:
        return ""
    
    ignore_prefixes = [
        'flac', 'Copyright', 'welcome to redistribute',
        'This program is free software', 'For more details'
    ]
    
    return '\n'.join(
        line.strip() for line in error.splitlines()
        if not any(line.strip().startswith(prefix) for prefix in ignore_prefixes)
        and line.strip()
    )

def is_file_accessible(file_path: str) -> bool:
    """Perform comprehensive checks on file accessibility without modification."""
    try:
        path = Path(file_path)
        
        # Basic existence and type check
        if not path.is_file():
            return False
        
        # Check if file is a symlink
        if path.is_symlink():
            try:
                real_path = path.resolve(strict=True)
                if not real_path.is_file():
                    return False
            except (OSError, RuntimeError):
                return False
        
        # Permission check - read-only
        if not os.access(file_path, os.R_OK):
            return False
        
        # Quick read test without modification
        try:
            with path.open('rb') as f:
                f.read(FILE_READ_CHUNK)
        except (IOError, OSError, PermissionError):
            return False
        
        # Check file size (0-byte files are invalid)
        return path.stat().st_size > 0
        
    except (OSError, PermissionError, UnicodeEncodeError):
        return False

def run_command(cmd: List[str], timeout: float, input_data: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a command with timeout and return (returncode, stdout, stderr)"""
    try:
        # Log the command being run (excluding file paths for brevity)
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Running command: {' '.join(cmd[:2])}...")
        
        with subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        ) as process:
            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=timeout
                )
                return process.returncode, stdout, stderr
            except subprocess.TimeoutExpired:
                process.kill()
                return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"

def verify_flac(file_path: str) -> VerificationResult:
    """Verify a FLAC file with comprehensive error handling, ensuring read-only access."""
    last_error = ""
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            if not is_file_accessible(file_path):
                if logging.getLogger().isEnabledFor(logging.INFO):
                    logging.info(f"File inaccessible: {file_path}")
                return VerificationResult(file_path, 'failed', "File inaccessible or unreadable")
            
            # FLAC verification - using 'flac -t' for read-only testing
            returncode, _, stderr = run_command(
                ['flac', '-t', file_path],
                timeout=FLAC_VERIFY_TIMEOUT
            )
            
            if returncode != 0:
                error_msg = clean_flac_error(stderr) or "Unknown FLAC error"
                if logging.getLogger().isEnabledFor(logging.INFO):
                    logging.info(f"FLAC verification failed for {file_path}: {error_msg}")
                return VerificationResult(file_path, 'failed', error_msg)
            
            # MD5 check using metaflac (read-only operation)
            returncode, stdout, stderr = run_command(
                ['metaflac', '--show-md5sum', file_path],
                timeout=MD5_CHECK_TIMEOUT
            )
            
            if returncode != 0:
                if attempt == MAX_RETRIES:
                    if logging.getLogger().isEnabledFor(logging.INFO):
                        logging.info(f"MD5 check failed for {file_path}")
                    return VerificationResult(file_path, 'failed', "MD5 check failed")
                time.sleep(0.5 * (attempt + 1))
                continue
                
            md5 = stdout.strip()
            if not md5 or md5 == '0'*32:
                if logging.getLogger().isEnabledFor(logging.INFO):
                    logging.info(f"No MD5 found in {file_path}")
                return VerificationResult(file_path, 'no_md5', None)
            
            if logging.getLogger().isEnabledFor(logging.DEBUG):
                logging.debug(f"File passed verification: {file_path}")
            return VerificationResult(file_path, 'passed', None, md5)
            
        except Exception as e:
            last_error = str(e)
            if attempt == MAX_RETRIES:
                error_msg = f"System error: {last_error}"
                if os.getenv('DEBUG_FLAC_CHECKER'):
                    error_msg += f"\n{traceback.format_exc()}"
                if logging.getLogger().isEnabledFor(logging.ERROR):
                    logging.error(f"Error processing {file_path}: {error_msg}")
                return VerificationResult(file_path, 'failed', error_msg)
            time.sleep(0.5 * (attempt + 1))
            
    return VerificationResult(file_path, 'failed', last_error)

def find_files(root_dir: str) -> Tuple[List[str], Dict[str, int]]:
    """Find all files in directory tree with file type counting."""
    flac_files = []
    file_types = Counter()
    total_files = 0
    
    try:
        root_path = Path(root_dir).resolve()
        if logging.getLogger().isEnabledFor(logging.INFO):
            logging.info(f"Searching for files in: {root_path}")
        
        # Track extensions we want to specifically count
        tracked_extensions = {
            '.flac', '.mp3', '.wav', '.aac', '.m4a', '.ogg',  # audio
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',  # images
            '.mp4', '.mkv', '.avi', '.mov', '.wmv',  # video
            '.lrc', '.txt', '.log', '.cue', '.pdf',  # text/docs
            '.zip', '.rar', '.7z', '.tar', '.gz'  # archives
        }
        
        for path in root_path.rglob('*'):
            try:
                if path.is_file() and is_file_accessible(str(path)):
                    total_files += 1
                    ext = path.suffix.lower()
                    
                    # Count all extensions, but for display, prioritize tracked ones
                    if ext in tracked_extensions:
                        file_types[ext] += 1
                    else:
                        file_types['other'] += 1
                    
                    # Add FLAC files to the processing list
                    if ext == '.flac':
                        flac_files.append(str(path))
                        if logging.getLogger().isEnabledFor(logging.DEBUG):
                            logging.debug(f"Found FLAC file: {path}")
            except (OSError, PermissionError, UnicodeError) as e:
                if logging.getLogger().isEnabledFor(logging.DEBUG):
                    logging.debug(f"Error accessing {path}: {str(e)}")
                continue
    
    except Exception as e:
        if logging.getLogger().isEnabledFor(logging.ERROR):
            logging.error(f"Error scanning directory {root_dir}: {str(e)}")
    
    # Add total count
    file_types['total'] = total_files
    
    return flac_files, file_types

def check_dependencies() -> bool:
    """Verify required tools are available in system PATH."""
    required_tools = ['flac', 'metaflac']
    missing = []
    
    for cmd in required_tools:
        if not shutil.which(cmd):
            missing.append(cmd)
    
    if missing:
        print(colors.colorize("Error: The following tools are required but not found:", 'orange_red'))
        for cmd in missing:
            print(f"  • {cmd}")
        
        # Additional help message for common platforms
        if 'flac' in missing or 'metaflac' in missing:
            print("\nInstallation help:")
            if sys.platform == 'win32':
                print("  Windows: Download FLAC from https://xiph.org/flac/download.html")
                print("           Make sure to add it to your PATH or place in the same directory")
            elif sys.platform == 'darwin':
                print("  macOS: Install with Homebrew: brew install flac")
            else:
                print("  Linux: Install with your package manager:")
                print("         Ubuntu/Debian: sudo apt install flac")
                print("         Fedora: sudo dnf install flac")
                print("         Arch: sudo pacman -S flac")
        
        if logging.getLogger().isEnabledFor(logging.ERROR):
            logging.error(f"Missing required tools: {', '.join(missing)}")
        return False
        
    return True

def print_header(version: str) -> None:
    """Print the program header with version information."""
    width = 80
    title = f"FLAC INTEGRITY CHECKER v{version}"
    
    print("\n" + "=" * width)
    print(colors.colorize(title.center(width), 'purple'))
    print(colors.colorize("Verify the integrity of your FLAC audio files".center(width), 'purple'))
    print("=" * width + "\n")

def print_file_table(file_types: Dict[str, int]) -> None:
    """Print a table of file types found during scanning."""
    if not file_types:
        return
    
    width = 60
    print(f"\n{' Files Found ':-^{width}}")
    
    # Format table rows
    table_data = []
    
    # Organize extensions into categories
    categories = {
        "Audio": ['.flac', '.mp3', '.wav', '.aac', '.m4a', '.ogg'],
        "Images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
        "Video": ['.mp4', '.mkv', '.avi', '.mov', '.wmv'],
        "Text/Docs": ['.lrc', '.txt', '.log', '.cue', '.pdf'],
        "Archives": ['.zip', '.rar', '.7z', '.tar', '.gz'],
    }
    
    # Print by category
    for category, extensions in categories.items():
        category_count = 0
        category_items = []
        
        for ext in extensions:
            count = file_types.get(ext, 0)
            if count > 0:
                category_count += count
                category_items.append(f"{ext[1:]}: {count}")
        
        if category_count > 0:
            print(colors.colorize(f"{category}:", 'purple'))
            # Print in rows of 3 items
            items_per_row = 3
            for i in range(0, len(category_items), items_per_row):
                row_items = category_items[i:i+items_per_row]
                print("  " + "  ".join(f"{item:<15}" for item in row_items))
    
    # Print other files if any
    other_count = file_types.get('other', 0)
    if other_count > 0:
        print(colors.colorize("Other:", 'purple'))
        print(f"  Other files: {other_count}")
    
    # Print total
    print("-" * width)
    print(colors.colorize(f"Total files: {file_types.get('total', 0)}", 'green'))
    print("-" * width + "\n")

def print_summary(results: Dict[str, int], 
                failed_files: List[Tuple[str, str]], 
                no_md5_files: List[str],
                log_filename: Optional[str] = None) -> None:
    """Print comprehensive summary of verification results."""
    total = sum(results.values())
    width = 80
    
    print(f"\n{' Verification Summary ':-^{width}}")
    print(colors.colorize(f"Total files checked: {total}", 'green'))
    print(colors.colorize(f"Passed verification: {results['passed']}", 'green'))
    print(colors.colorize(f"Failed verification: {results['failed']}", 'orange_red'))
    print(colors.colorize(f"Files without MD5: {results['no_md5']}", 'yellow'))
    
    if log_filename:
        print(colors.colorize(f"Log file created: {log_filename}", 'purple'))
    
    print('-' * width)

    if results['failed']:
        print(colors.colorize("Failed files:", 'orange_red'))
        for i, (file, error) in enumerate(failed_files, 1):
            print(f"{colors.colorize(f'{i}.', 'orange_red')} {colors.colorize(file, 'orange_red')}")
            if error:
                for line in error.splitlines():
                    if line.strip():
                        print(f"   {line.strip()}")
        print('-' * width)

    if results['no_md5']:
        print(colors.colorize("Files without MD5 checksums:", 'yellow'))
        for i, file in enumerate(no_md5_files, 1):
            relative_path = os.path.relpath(file)
            print(f"{colors.colorize(f'{i}.', 'yellow')} {colors.colorize(relative_path, 'yellow')}")
        print('-' * width)

def normalize_path(path: str) -> str:
    """
    Normalize path by handling quotes, trailing slashes and converting to absolute path properly.
    Works with both Windows and Unix-style paths.
    """
    if not path:
        return os.path.abspath('.')
    
    # Remove any surrounding quotes that might have been passed through
    path = path.strip('"\'')
    
    # Handle paths with spaces or special characters
    try:
        # Convert to Path object which handles OS-specific path formatting
        path_obj = Path(path)
        
        # Convert back to string and get absolute path
        abs_path = os.path.abspath(str(path_obj))
        
        return abs_path
    except Exception as e:
        # If there's any error, fall back to a simple approach
        return os.path.abspath(path)

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=f"FLAC Integrity Checker v{VERSION} - Verify the integrity of FLAC audio files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('-d', '--directory', 
                        help='Directory to scan (default: current directory)', 
                        default='.')
    
    parser.add_argument('-l', '--log', 
                        action='store_true',
                        help='Create a log file of the verification process')
    
    parser.add_argument('-v', '--verbose', 
                        action='store_true',
                        help='Enable verbose output')
    
    parser.add_argument('--version', 
                        action='version', 
                        version=f'FLAC Integrity Checker v{VERSION}')
    
    return parser.parse_args()

def main() -> None:
    """Main execution function."""
    try:
        args = parse_arguments()
        
        # Setup logging if enabled
        log_file = None
        if args.log:
            log_level = logging.DEBUG if args.verbose else logging.INFO
            log_file = setup_logging(True)
            logging.getLogger().setLevel(log_level)
        
        # Print header
        print_header(VERSION)
        
        # Check dependencies
        if not check_dependencies():
            sys.exit(1)
        
        # Get target directory - properly normalize the path
        try:
            target_dir = normalize_path(args.directory)
            print(f"Target directory: {target_dir}")
            
            # Check if directory exists
            if not os.path.isdir(target_dir):
                print(colors.colorize(f"Error: Directory not found: {target_dir}", 'orange_red'))
                print(colors.colorize("Try using double quotes around directory paths with spaces:", 'orange_red'))
                print(f'  Example: python {sys.argv[0]} -d "Your Folder Name"')
                
                if args.log:
                    logging.error(f"Directory not found: {target_dir}")
                sys.exit(1)
        except Exception as e:
            print(colors.colorize(f"Error processing directory path: {str(e)}", 'orange_red'))
            print(colors.colorize("Try using double quotes around directory paths with spaces:", 'orange_red'))
            print(f'  Example: python {sys.argv[0]} -d "Your Folder Name"')
            
            if args.log:
                logging.error(f"Error processing directory path: {str(e)}")
            sys.exit(1)
            
        print("Searching for files...")
        
        try:
            flac_files, file_types = find_files(target_dir)
        except Exception as e:
            print(colors.colorize(f"Error searching for files: {str(e)}", 'orange_red'))
            if args.log:
                logging.error(f"Error searching for files: {str(e)}")
            sys.exit(1)
        
        # Print file type statistics
        print_file_table(file_types)
        
        if not flac_files:
            print(colors.colorize("No FLAC files found for verification.", 'yellow'))
            if args.log:
                logging.info("No FLAC files found for verification.")
            sys.exit(0)
        
        print(colors.colorize(f"Starting verification of {len(flac_files)} FLAC files", 'green'))
        if args.log:
            logging.info(f"Starting verification of {len(flac_files)} FLAC files")
        
        thread_count = get_optimal_threads()
        print(f"Using {thread_count} threads for verification...")
        if args.log:
            logging.info(f"Using {thread_count} threads for verification")
        
        results = {'passed': 0, 'failed': 0, 'no_md5': 0}
        failed_files = []
        no_md5_files = []
        
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=thread_count,
                thread_name_prefix='flac_verify'
            ) as executor:
                futures = {executor.submit(verify_flac, f): f for f in flac_files}
                
                # Progress bar if tqdm is available
                progress_bar = None
                if tqdm:
                    progress_bar = tqdm(
                        total=len(futures),
                        unit="file",
                        leave=True,
                        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
                    )
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result.status == 'passed':
                            results['passed'] += 1
                            if args.log and args.verbose:
                                logging.debug(f"Passed: {result.file_path}")
                        elif result.status == 'failed':
                            results['failed'] += 1
                            failed_files.append((result.file_path, result.error or ""))
                            if args.log:
                                logging.warning(f"Failed: {result.file_path} - {result.error}")
                        else:
                            results['no_md5'] += 1
                            no_md5_files.append(result.file_path)
                            if args.log:
                                logging.info(f"No MD5: {result.file_path}")
                    except Exception as e:
                        file = futures[future]
                        results['failed'] += 1
                        error_msg = f"Processing error: {str(e)}"
                        failed_files.append((file, error_msg))
                        if args.log:
                            logging.error(f"Error processing {file}: {str(e)}")
                    finally:
                        if progress_bar:
                            progress_bar.update(1)
                
                if progress_bar:
                    progress_bar.close()
        
        except KeyboardInterrupt:
            print(colors.colorize("\nVerification interrupted by user.", 'orange_red'))
            if args.log:
                logging.warning("Verification interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(colors.colorize(f"\nError during verification: {str(e)}", 'orange_red'))
            if args.log:
                logging.error(f"Error during verification: {str(e)}")
                if os.getenv('DEBUG_FLAC_CHECKER'):
                    logging.error(traceback.format_exc())
            sys.exit(1)
        
        print(colors.colorize("\nVerification Complete", 'purple'))
        if args.log:
            logging.info("Verification Complete")
            logging.info(f"Results: Passed={results['passed']}, Failed={results['failed']}, No MD5={results['no_md5']}")
        
        print_summary(results, failed_files, no_md5_files, log_file)
        
        # Exit with error code if any failures were found
        sys.exit(1 if results['failed'] else 0)
        
    except KeyboardInterrupt:
        print(colors.colorize("\nOperation cancelled by user.", 'orange_red'))
        if 'logging' in sys.modules and logging.getLogger().hasHandlers():
            logging.warning("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(colors.colorize(f"\nUnexpected error: {str(e)}", 'orange_red'))
        if 'logging' in sys.modules and logging.getLogger().hasHandlers():
            logging.critical(f"Unexpected error: {str(e)}")
            if os.getenv('DEBUG_FLAC_CHECKER'):
                logging.critical(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()