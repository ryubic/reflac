#!/usr/bin/env python3
"""
FLAC Integrity Checker - A robust tool for verifying FLAC file integrity
with parallel processing and comprehensive error reporting.
"""

import subprocess
import os
import concurrent.futures
from tqdm import tqdm
import multiprocessing
import sys
import shutil
import traceback
import time
from typing import List, Tuple, Optional, Dict

# Constants
MAX_THREADS = 32  # Safety limit for maximum threads
MAX_RETRIES = 2  # Number of retries for failed operations
FILE_READ_CHUNK = 8192  # Chunk size for file reading checks

# Color setup (keeping original scheme)
try:
    from colorama import init, Fore, Style
    init()
    COLOR_ENABLED = True
    ORANGE_RED = '\033[38;5;202m'
    DULL_YELLOW = '\033[38;5;179m'
    BRIGHT_GREEN = '\033[92m'
    HEADER_COLOR = '\033[96m'  # Bright cyan for header
except ImportError:
    COLOR_ENABLED = False
    ORANGE_RED = DULL_YELLOW = BRIGHT_GREEN = HEADER_COLOR = ''

def color_text(text: str, color: str) -> str:
    """Color formatter (original version)"""
    if not COLOR_ENABLED:
        return text
    colors = {
        'green': BRIGHT_GREEN,
        'orange_red': ORANGE_RED,
        'dull_yellow': DULL_YELLOW,
        'header': HEADER_COLOR,
        'reset': Style.RESET_ALL
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"

def get_optimal_threads() -> int:
    """Calculate optimal number of threads with safety limits."""
    try:
        cpu_count = multiprocessing.cpu_count()
        # Use 80% of cores with min 1, max MAX_THREADS (original calculation)
        return min(MAX_THREADS, max(1, int(cpu_count * 0.8)))
    except:
        return 1  # Fallback to single thread if detection fails

def clean_flac_error(error: str) -> str:
    """Clean up FLAC error messages (original version)."""
    if not error:
        return ""
    return '\n'.join(
        line.strip() for line in error.splitlines()
        if not any(line.startswith(x) for x in [
            'flac', 'Copyright', 'welcome to redistribute'
        ]) and line.strip()
    )

def is_file_accessible(file_path: str) -> bool:
    """Perform comprehensive checks on file accessibility."""
    try:
        # Basic existence and type check
        if not os.path.isfile(file_path):
            return False
        
        # Check if file is a symlink
        if os.path.islink(file_path):
            try:
                real_path = os.path.realpath(file_path)
                if not os.path.isfile(real_path):
                    return False
            except OSError:
                return False
        
        # Permission check
        if not os.access(file_path, os.R_OK):
            return False
        
        # Quick read test with explicit handle closing
        try:
            with open(file_path, 'rb') as f:
                f.read(FILE_READ_CHUNK)
        except (IOError, OSError, PermissionError):
            return False
        
        # Check file size (0-byte files are invalid)
        try:
            if os.path.getsize(file_path) == 0:
                return False
        except OSError:
            return False
            
        return True
    except (OSError, PermissionError, UnicodeEncodeError):
        return False

def verify_flac(file_path: str) -> Tuple[str, str, Optional[str]]:
    """
    Verify a FLAC file with comprehensive error handling.
    Returns tuple of (file_path, status, error_message)
    """
    # Pre-flight checks with retries
    for attempt in range(MAX_RETRIES + 1):
        try:
            if not is_file_accessible(file_path):
                return (file_path, 'failed', "File inaccessible or unreadable")
            
            # FLAC verification with context manager
            try:
                with subprocess.Popen(
                    ['flac', '-t', file_path],
                    stderr=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                ) as process:
                    try:
                        _, stderr = process.communicate(timeout=30)
                        returncode = process.returncode
                    except subprocess.TimeoutExpired:
                        process.kill()
                        return (file_path, 'failed', "Verification timed out")
            except FileNotFoundError:
                return (file_path, 'failed', "flac command not found")
                
            error_msg = clean_flac_error(stderr)
            
            if returncode != 0:
                return (file_path, 'failed', error_msg or "Unknown FLAC error")
            
            # MD5 check with retries and context manager
            for md5_attempt in range(MAX_RETRIES + 1):
                try:
                    with subprocess.Popen(
                        ['metaflac', '--show-md5sum', file_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                    ) as process:
                        try:
                            stdout, _ = process.communicate(timeout=10)
                            md5 = stdout.strip()
                            break
                        except subprocess.TimeoutExpired:
                            if md5_attempt == MAX_RETRIES:
                                return (file_path, 'failed', "MD5 check timed out")
                            time.sleep(0.5 * (md5_attempt + 1))
                            continue
                except (OSError, subprocess.SubprocessError):
                    if md5_attempt == MAX_RETRIES:
                        return (file_path, 'failed', "MD5 check failed")
                    time.sleep(0.5 * (md5_attempt + 1))
                    continue
            
            if not md5 or md5 == '0'*32:
                return (file_path, 'no_md5', None)
                
            return (file_path, 'passed', None)
            
        except Exception as e:
            if attempt == MAX_RETRIES:
                error_msg = f"System error: {str(e)}"
                if os.getenv('DEBUG_FLAC_CHECKER'):
                    error_msg += f"\n{traceback.format_exc()}"
                return (file_path, 'failed', error_msg)
            time.sleep(0.5 * (attempt + 1))
            continue

def find_flac_files(root_dir: str) -> List[str]:
    """
    Find all FLAC files in directory tree with robust error handling.
    Returns list of absolute file paths.
    """
    flac_files = []
    processed_dirs = set()
    
    try:
        root_dir = os.path.abspath(root_dir)
    except OSError:
        return []
    
    for root, dirs, files in os.walk(root_dir, onerror=lambda e: None):
        # Skip directories we can't access
        try:
            abs_root = os.path.abspath(root)
            if abs_root in processed_dirs:
                continue
            processed_dirs.add(abs_root)
        except OSError:
            continue
        
        for f in files:
            try:
                if f.lower().endswith('.flac'):
                    try:
                        path = os.path.abspath(os.path.join(root, f))
                        if os.path.isfile(path) and is_file_accessible(path):
                            flac_files.append(path)
                    except (OSError, PermissionError, UnicodeEncodeError):
                        continue
            except UnicodeDecodeError:
                continue  # Skip files with encoding issues in their names
    
    return flac_files

def check_dependencies() -> None:
    """Verify required tools are available in system PATH."""
    required_tools = ['flac', 'metaflac']
    missing = []
    
    for cmd in required_tools:
        try:
            if not shutil.which(cmd):
                missing.append(cmd)
        except (OSError, AttributeError):
            missing.append(cmd)
    
    if missing:
        print(color_text("Error: The following tools are required but not found:", 'orange_red'))
        for cmd in missing:
            print(f"  • {cmd}")
        sys.exit(1)

def format_error_message(error: str) -> str:
    """Format error messages for clean display (original version)."""
    if not error:
        return ""
    lines = error.splitlines()
    return '\n'.join(
        f"   {line.strip()}" if i > 0 else line.strip()
        for i, line in enumerate(lines)
        if line.strip()
    )

def print_summary(results: Dict[str, int], failed_files: List[Tuple[str, str]], 
                no_md5_files: List[str]) -> None:
    """Print comprehensive summary of verification results."""
    total = sum(results.values())
    
    print(color_text(f"\nTotal files checked: {total}", 'green'))
    print(color_text(f"Passed verification: {results['passed']}", 'green'))
    print(color_text(f"Failed verification: {results['failed']}", 'orange_red'))
    print(color_text(f"Files without MD5: {results['no_md5']}", 'dull_yellow'))

    # Separator line - fixed 80 characters
    print("\n" + "-" * 80)

    if results['failed']:
        print(color_text("Failed files:", 'orange_red'))
        for i, (file, error) in enumerate(failed_files, 1):
            print(f"{color_text(f'{i}.', 'orange_red')} {color_text(file, 'orange_red')}")
            if error:
                error_lines = error.splitlines()
                for line in error_lines:
                    if line.strip():
                        print(f"   {line.strip()}")
        print("-" * 80)

    if results['no_md5']:
        print(color_text("Files without MD5 checksums:", 'dull_yellow'))
        for i, file in enumerate(no_md5_files, 1):
            print(f"{color_text(f'{i}.', 'dull_yellow')} {color_text(file, 'dull_yellow')}")
        print("-" * 80)

def main() -> None:
    """Main execution function."""
    try:
        check_dependencies()
        
        # Print header only once at start
        header_title = "FLAC INTEGRITY CHECKER"
        header_line = '-' * len(header_title)
        print(f"\n{header_line}")
        print(header_title)
        print(f"{header_line}\n")
        
        print("Searching for FLAC files...")
        
        try:
            flac_files = find_flac_files('.')
        except Exception as e:
            print(color_text(f"\nError searching for files: {str(e)}", 'orange_red'))
            sys.exit(1)
        
        if not flac_files:
            print("No FLAC files found.")
            sys.exit(0)
        
        print(f"Found {len(flac_files)} files.")
        
        thread_count = get_optimal_threads()
        print(f"Starting verification using {thread_count} threads...")
        
        results = {'passed': 0, 'failed': 0, 'no_md5': 0}
        failed_files = []
        no_md5_files = []
        
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=thread_count,
                thread_name_prefix='flac_verify'
            ) as executor:
                futures = {executor.submit(verify_flac, f): f for f in flac_files}
                
                # Changed leave=True to keep progress bar visible
                with tqdm(total=len(futures), unit="file", leave=True) as pbar:
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            file, status, error = future.result()
                            if status == 'passed':
                                results['passed'] += 1
                            elif status == 'failed':
                                results['failed'] += 1
                                failed_files.append((file, error))
                            else:
                                results['no_md5'] += 1
                                no_md5_files.append(file)
                        except Exception as e:
                            file = futures[future]
                            results['failed'] += 1
                            failed_files.append((file, f"Processing error: {str(e)}"))
                        finally:
                            pbar.update(1)
        
        except KeyboardInterrupt:
            print(color_text("\n\nVerification interrupted by user.", 'orange_red'))
            sys.exit(1)
        except Exception as e:
            print(color_text(f"\nError during verification: {str(e)}", 'orange_red'))
            sys.exit(1)
        
        print("Verification Complete!")
        print_summary(results, failed_files, no_md5_files)
        
        sys.exit(1 if results['failed'] else 0)
        
    except KeyboardInterrupt:
        print(color_text("\nOperation cancelled by user.", 'orange_red'))
        sys.exit(1)
    except Exception as e:
        print(color_text(f"\nUnexpected error: {str(e)}", 'orange_red'))
        if os.getenv('DEBUG_FLAC_CHECKER'):
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()