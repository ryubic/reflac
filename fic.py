#!/usr/bin/env python3
"""
FLAC Integrity Checker - A robust tool for verifying FLAC file integrity
with parallel processing, comprehensive error reporting, and logging capabilities.

Usage:
  - To scan current directory: python fic.py
  - To scan specific directory: python fic.py -d /path/to/directory
  - To create a log file: python fic.py -l
  - To scan specific directory and create log: python fic.py -d /path/to/directory -l
  - Additional options: --max-threads N, --timeout S
"""

import argparse
import concurrent.futures
import logging
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
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

VERSION = "1.4"
FILE_READ_CHUNK = 8192  # Chunk size for file reading checks

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
            self.lavender = '\033[38;5;147m'      # Info/header color
            self.reset = Style.RESET_ALL
        except ImportError:
            self.enabled = False
            self.orange_red = self.yellow = self.green = self.lavender = self.reset = ''

    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if enabled"""
        if not self.enabled:
            return text
        color_code = getattr(self, color, '')
        return f"{color_code}{text}{self.reset}"

class VerificationResult(NamedTuple):
    """Container for verification results"""
    file_path: str
    status: str  # 'passed', 'failed', or 'no_md5'
    error: Optional[str]
    md5sum: Optional[str] = None

def setup_logging(enable_logging: bool, verbose: bool) -> Tuple[Optional[str], Optional[QueueListener]]:
    """Configure thread-safe logging to file and console if enabled"""
    if not enable_logging:
        return None, None
        
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_filename = f"flac_check_{timestamp}.log"
    
    log_queue = Queue()
    queue_handler = QueueHandler(log_queue)
    
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S'))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.ERROR)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.addHandler(queue_handler)
    
    listener = QueueListener(log_queue, file_handler, console_handler)
    listener.start()
    
    logging.info(f"FLAC Integrity Checker v{VERSION} started")
    return log_filename, listener

def get_optimal_threads(max_threads: int) -> int:
    """Calculate optimal number of threads with safety limits."""
    try:
        cpu_count = multiprocessing.cpu_count()
        return min(max_threads, max(1, int(cpu_count * 0.75)))
    except NotImplementedError:
        logging.info(f"Thread detection failed: falling back to single thread")
        return 1  # Fallback to single thread if detection fails

def clean_flac_error(error: str) -> str:
    """Clean up FLAC error messages with early return."""
    if not error or not error.strip():
        return ""
    
    ignore_prefixes = ['flac', 'Copyright', 'welcome to redistribute', 'This program is free software', 'For more details']
    return '\n'.join(line.strip() for line in error.splitlines() 
                    if line.strip() and not any(line.strip().startswith(prefix) for prefix in ignore_prefixes))

def is_file_accessible(file_path: str) -> bool:
    """Perform comprehensive checks on file accessibility without modification."""
    try:
        path = Path(file_path)
        if not path.is_file():
            return False
        
        if path.is_symlink():
            try:
                real_path = path.resolve(strict=True)
                if not real_path.is_file():
                    return False
            except (OSError, RuntimeError):
                return False
        
        if not os.access(file_path, os.R_OK):
            return False
        
        with path.open('rb') as f:
            f.read(FILE_READ_CHUNK)
        
        return path.stat().st_size > 0
    except (OSError, PermissionError, UnicodeEncodeError):
        return False

def run_command(cmd: List[str], timeout: float, input_data: Optional[str] = None) -> Tuple[int, str, str]:
    """Run a command with timeout and return (returncode, stdout, stderr)"""
    logging.debug(f"Running command: {' '.join(cmd[:2])}...")
    try:
        with subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        ) as process:
            try:
                stdout, stderr = process.communicate(input=input_data, timeout=timeout)
                return process.returncode, stdout, stderr
            except subprocess.TimeoutExpired:
                process.kill()
                return -1, "", "Command timed out"
    except FileNotFoundError:
        return -1, "", f"Command not found: {cmd[0]}"
    except (OSError, subprocess.SubprocessError) as e:
        return -1, "", f"Subprocess error: {str(e)}"

def verify_flac(file_path: str, timeout: float, max_retries: int, verbose: bool) -> VerificationResult:
    """Verify a FLAC file with comprehensive error handling, ensuring read-only access."""
    last_error = ""
    
    for attempt in range(max_retries + 1):
        try:
            if not is_file_accessible(file_path):
                logging.info(f"File inaccessible: {file_path}")
                return VerificationResult(file_path, 'failed', "File inaccessible or unreadable")
            
            returncode, _, stderr = run_command(['flac', '-t', file_path], timeout=timeout)
            if returncode != 0:
                error_msg = clean_flac_error(stderr) or "Unknown FLAC error"
                logging.info(f"FLAC verification failed for {file_path}: {error_msg}")
                return VerificationResult(file_path, 'failed', error_msg)
            
            returncode, stdout, stderr = run_command(['metaflac', '--show-md5sum', file_path], timeout=timeout/3)
            if returncode != 0:
                if attempt == max_retries:
                    logging.info(f"MD5 check failed for {file_path}")
                    return VerificationResult(file_path, 'failed', "MD5 check failed")
                time.sleep(0.5 * (attempt + 1))
                continue
                
            md5 = stdout.strip()
            if not md5 or md5 == '0'*32:
                logging.info(f"No MD5 found in {file_path}")
                return VerificationResult(file_path, 'no_md5', None)
            
            logging.debug(f"File passed verification: {file_path}")
            return VerificationResult(file_path, 'passed', None, md5)
            
        except (OSError, subprocess.SubprocessError) as e:
            last_error = str(e)
            if attempt == max_retries:
                error_msg = f"System error: {last_error}"
                if verbose:
                    error_msg += f"\n{traceback.format_exc()}"
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
        logging.info(f"Searching for files in: {root_path}")
        
        tracked_extensions = {
            '.flac', '.mp3', '.wav', '.aac', '.m4a', '.ogg',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
            '.mp4', '.mkv', '.avi', '.mov', '.wmv',
            '.lrc', '.txt', '.log', '.cue', '.pdf',
            '.zip', '.rar', '.7z', '.tar', '.gz'
        }
        
        for path in root_path.rglob('*'):
            try:
                if path.is_file() and is_file_accessible(str(path)):
                    total_files += 1
                    ext = path.suffix.lower()
                    if ext in tracked_extensions:
                        file_types[ext] += 1
                    else:
                        file_types['other'] += 1
                    
                    if ext == '.flac':
                        flac_files.append(str(path))
                        logging.debug(f"Found FLAC file: {path}")
            except (OSError, PermissionError, UnicodeError) as e:
                logging.debug(f"Error accessing {path}: {str(e)}")
                continue
    
    except (OSError, PermissionError) as e:
        logging.error(f"Error scanning directory {root_dir}: {str(e)}")
    
    file_types['total'] = total_files
    return flac_files, file_types

def check_dependencies(colors: Colors) -> bool:
    """Verify required tools are available in system PATH."""
    required_tools = ['flac', 'metaflac']
    missing = [cmd for cmd in required_tools if not shutil.which(cmd)]
    
    if missing:
        print(colors.colorize("Error: The following tools are required but not found:", 'orange_red'))
        for cmd in missing:
            print(f"  • {cmd}")
        
        if 'flac' in missing or 'metaflac' in missing:
            print("\nInstallation help:")
            if sys.platform == 'win32':
                print("  Windows: Download FLAC from https://xiph.org/flac/download.html")
                print("           Add to PATH or place in the same directory")
            elif sys.platform == 'darwin':
                print("  macOS: Install with Homebrew: brew install flac")
            else:
                print("  Linux: Install with your package manager:")
                print("         Ubuntu/Debian: sudo apt install flac")
                print("         Fedora: sudo dnf install flac")
                print("         Arch: sudo pacman -S flac")
        
        logging.error(f"Missing required tools: {', '.join(missing)}")
        return False
    return True

def print_header(version: str, colors: Colors) -> None:
    """Print the program header with version information."""
    width = 80
    title = f"FLAC INTEGRITY CHECKER v{version}"
    print("\n" + "=" * width)
    print(colors.colorize(title.center(width), 'lavender'))
    print(colors.colorize("Verify the integrity of your FLAC audio files".center(width), 'lavender'))
    print("=" * width + "\n")

def print_file_table(file_types: Dict[str, int], colors: Colors) -> None:
    """Print a table of file types found during scanning."""
    if not file_types:
        return
    
    width = 60
    print(f"\n{' Files Found ':-^{width}}")
    
    categories = {
        "Audio": ['.flac', '.mp3', '.wav', '.aac', '.m4a', '.ogg'],
        "Images": ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'],
        "Video": ['.mp4', '.mkv', '.avi', '.mov', '.wmv'],
        "Text/Docs": ['.lrc', '.txt', '.log', '.cue', '.pdf'],
        "Archives": ['.zip', '.rar', '.7z', '.tar', '.gz'],
    }
    
    for category, extensions in categories.items():
        category_count = 0
        category_items = []
        for ext in extensions:
            count = file_types.get(ext, 0)
            if count > 0:
                category_count += count
                category_items.append(f"{ext[1:]}: {count}")
        
        if category_count > 0:
            print(colors.colorize(f"{category}:", 'lavender'))
            items_per_row = 3
            for i in range(0, len(category_items), items_per_row):
                row_items = category_items[i:i+items_per_row]
                print("  " + "  ".join(f"{item:<15}" for item in row_items))
    
    other_count = file_types.get('other', 0)
    if other_count > 0:
        print(colors.colorize("Other:", 'lavender'))
        print(f"  Other files: {other_count}")
    
    print("-" * width)
    print(colors.colorize(f"Total files: {file_types.get('total', 0)}", 'green'))
    print("-" * width + "\n")

def print_summary(results: Dict[str, int], failed_files: List[Tuple[str, str]], 
                 no_md5_files: List[str], log_filename: Optional[str], colors: Colors) -> None:
    """Print comprehensive summary of verification results."""
    total = sum(results.values())
    width = 80
    
    print(f"\n{' Verification Summary ':-^{width}}")
    print(colors.colorize(f"Total files checked: {total}", 'green'))
    print(colors.colorize(f"Passed verification: {results['passed']}", 'green'))
    print(colors.colorize(f"Failed verification: {results['failed']}", 'orange_red'))
    print(colors.colorize(f"Files without MD5: {results['no_md5']}", 'yellow'))
    
    if log_filename:
        print(colors.colorize(f"Log file created: {log_filename}", 'lavender'))
    
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
    """Normalize path with input validation."""
    if not isinstance(path, str) or not path.strip():
        return os.path.abspath('.')
    
    path = path.strip('"\'')
    try:
        path_obj = Path(path)
        return os.path.abspath(str(path_obj))
    except (ValueError, OSError) as e:
        logging.warning(f"Invalid path {path}: {str(e)}")
        return os.path.abspath(path)

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments with added options."""
    parser = argparse.ArgumentParser(
        description=f"FLAC Integrity Checker v{VERSION} - Verify the integrity of FLAC audio files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('-d', '--directory', help='Directory to scan', default='.')
    parser.add_argument('-l', '--log', action='store_true', help='Create a log file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--max-threads', type=int, default=32, help='Maximum number of threads')
    parser.add_argument('--timeout', type=int, default=30, help='Timeout for FLAC verification in seconds')
    parser.add_argument('--max-retries', type=int, default=2, help='Number of retries for failed operations')
    parser.add_argument('--version', action='version', version=f'FLAC Integrity Checker v{VERSION}')
    return parser.parse_args()

def main() -> None:
    """Main execution function."""
    try:
        args = parse_arguments()
        colors = Colors()
        
        log_file, log_listener = setup_logging(args.log, args.verbose)
        if args.log and log_listener:
            logging.getLogger().setLevel(logging.DEBUG if args.verbose else logging.INFO)
        
        print_header(VERSION, colors)
        if not check_dependencies(colors):
            sys.exit(1)
        
        target_dir = normalize_path(args.directory)
        print(f"Target directory: {target_dir}")
        if not os.path.isdir(target_dir):
            print(colors.colorize(f"Error: Directory not found: {target_dir}", 'orange_red'))
            print(colors.colorize("Try using double quotes around paths with spaces:", 'orange_red'))
            print(f'  Example: python {sys.argv[0]} -d "Your Folder Name"')
            if args.log:
                logging.error(f"Directory not found: {target_dir}")
            sys.exit(1)
            
        print("Searching for files...")
        flac_files, file_types = find_files(target_dir)
        print_file_table(file_types, colors)
        
        if not flac_files:
            print(colors.colorize("No FLAC files found for verification.", 'yellow'))
            if args.log:
                logging.info("No FLAC files found for verification.")
            sys.exit(0)
        
        if not tqdm and args.verbose:
            print(colors.colorize("Progress bar unavailable: install 'tqdm' for progress tracking.", 'yellow'))
        
        print(colors.colorize(f"Starting verification of {len(flac_files)} FLAC files", 'green'))
        if args.log:
            logging.info(f"Starting verification of {len(flac_files)} FLAC files")
        
        thread_count = get_optimal_threads(args.max_threads)
        print(f"Using {thread_count} threads for verification...")
        if args.log:
            logging.info(f"Using {thread_count} threads for verification")
        
        results = {'passed': 0, 'failed': 0, 'no_md5': 0}
        failed_files = []
        no_md5_files = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=thread_count, thread_name_prefix='flac_verify') as executor:
            futures = {executor.submit(verify_flac, f, args.timeout, args.max_retries, args.verbose): f for f in flac_files}
            progress_bar = tqdm(total=len(futures), unit="file", leave=True, 
                               bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]") if tqdm else None
            
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
                except (OSError, subprocess.SubprocessError) as e:
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
        
        print(colors.colorize("\nVerification Complete", 'lavender'))
        if args.log:
            logging.info("Verification Complete")
            logging.info(f"Results: Passed={results['passed']}, Failed={results['failed']}, No MD5={results['no_md5']}")
        
        print_summary(results, failed_files, no_md5_files, log_file, colors)
        if log_listener:
            log_listener.stop()
        
        sys.exit(1 if results['failed'] else 0)
        
    except KeyboardInterrupt:
        print(colors.colorize("\nOperation cancelled by user.", 'orange_red'))
        if args.log:
            logging.warning("Operation cancelled by user")
        if 'log_listener' in locals() and log_listener:
            log_listener.stop()
        sys.exit(1)
    except (OSError, ValueError) as e:
        print(colors.colorize(f"\nUnexpected error: {str(e)}", 'orange_red'))
        if args.log:
            logging.critical(f"Unexpected error: {str(e)}")
        if 'log_listener' in locals() and log_listener:
            log_listener.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()