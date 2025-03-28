#!/usr/bin/env python3
"""
FLAC Integrity Checker - A robust tool for verifying FLAC file integrity
with parallel processing and comprehensive error reporting.
"""

import concurrent.futures
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

# Constants
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
            from colorama import init, Fore, Style
            init()
            self.enabled = True
            self.orange_red = '\033[38;5;202m'
            self.dull_yellow = '\033[38;5;179m'
            self.green = '\033[92m'
            self.header = '\033[96m'  # Bright cyan for header
            self.reset = Style.RESET_ALL
        except ImportError:
            self.enabled = False
            self.orange_red = self.dull_yellow = self.green = self.header = self.reset = ''

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

def get_optimal_threads() -> int:
    """Calculate optimal number of threads with safety limits."""
    try:
        cpu_count = multiprocessing.cpu_count()
        # Use 60% of cores with min 1, max MAX_THREADS
        return min(MAX_THREADS, max(1, int(cpu_count * 0.6)))
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
    """Perform comprehensive checks on file accessibility."""
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
        
        # Permission check
        if not os.access(file_path, os.R_OK):
            return False
        
        # Quick read test
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
    """Verify a FLAC file with comprehensive error handling."""
    last_error = ""
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            if not is_file_accessible(file_path):
                return VerificationResult(file_path, 'failed', "File inaccessible or unreadable")
            
            # FLAC verification
            returncode, _, stderr = run_command(
                ['flac', '-t', file_path],
                timeout=FLAC_VERIFY_TIMEOUT
            )
            
            if returncode != 0:
                error_msg = clean_flac_error(stderr) or "Unknown FLAC error"
                return VerificationResult(file_path, 'failed', error_msg)
            
            # MD5 check
            returncode, stdout, stderr = run_command(
                ['metaflac', '--show-md5sum', file_path],
                timeout=MD5_CHECK_TIMEOUT
            )
            
            if returncode != 0:
                if attempt == MAX_RETRIES:
                    return VerificationResult(file_path, 'failed', "MD5 check failed")
                time.sleep(0.5 * (attempt + 1))
                continue
                
            md5 = stdout.strip()
            if not md5 or md5 == '0'*32:
                return VerificationResult(file_path, 'no_md5', None)
                
            return VerificationResult(file_path, 'passed', None)
            
        except Exception as e:
            last_error = str(e)
            if attempt == MAX_RETRIES:
                error_msg = f"System error: {last_error}"
                if os.getenv('DEBUG_FLAC_CHECKER'):
                    error_msg += f"\n{traceback.format_exc()}"
                return VerificationResult(file_path, 'failed', error_msg)
            time.sleep(0.5 * (attempt + 1))
            
    return VerificationResult(file_path, 'failed', last_error)

def find_flac_files(root_dir: str) -> List[str]:
    """Find all FLAC files in directory tree with robust error handling."""
    flac_files = []
    root_path = Path(root_dir).resolve()
    
    for path in root_path.rglob('*.flac'):
        try:
            if path.is_file() and is_file_accessible(str(path)):
                flac_files.append(str(path))
        except (OSError, PermissionError, UnicodeError):
            continue
    
    return flac_files

def check_dependencies() -> None:
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
        sys.exit(1)

def print_summary(results: Dict[str, int], 
                failed_files: List[Tuple[str, str]], 
                no_md5_files: List[str]) -> None:
    """Print comprehensive summary of verification results."""
    total = sum(results.values())
    width = 80
    
    print(colors.colorize(f"\n{' Verification Summary ':-^{width}}", 'header'))
    print(colors.colorize(f"Total files checked: {total}", 'green'))
    print(colors.colorize(f"Passed verification: {results['passed']}", 'green'))
    print(colors.colorize(f"Failed verification: {results['failed']}", 'orange_red'))
    print(colors.colorize(f"Files without MD5: {results['no_md5']}", 'dull_yellow'))
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
        print(colors.colorize("Files without MD5 checksums:", 'dull_yellow'))
        for i, file in enumerate(no_md5_files, 1):
            print(f"{colors.colorize(f'{i}.', 'dull_yellow')} {colors.colorize(file, 'dull_yellow')}")
        print('-' * width)

def main() -> None:
    """Main execution function."""
    try:
        check_dependencies()
        
        # Print header
        title = "FLAC INTEGRITY CHECKER"
        print(f"\n{colors.colorize(title, 'header')}")
        print(colors.colorize('-' * len(title), 'header'))
        
        print("\nSearching for FLAC files...")
        
        try:
            flac_files = find_flac_files('.')
        except Exception as e:
            print(colors.colorize(f"\nError searching for files: {str(e)}", 'orange_red'))
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
                
                # Progress bar if tqdm is available
                progress_bar = tqdm(
                    total=len(futures),
                    unit="file",
                    leave=True,
                    disable=not tqdm
                )
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result.status == 'passed':
                            results['passed'] += 1
                        elif result.status == 'failed':
                            results['failed'] += 1
                            failed_files.append((result.file_path, result.error or ""))
                        else:
                            results['no_md5'] += 1
                            no_md5_files.append(result.file_path)
                    except Exception as e:
                        file = futures[future]
                        results['failed'] += 1
                        failed_files.append((file, f"Processing error: {str(e)}"))
                    finally:
                        progress_bar.update(1)
                
                progress_bar.close()
        
        except KeyboardInterrupt:
            print(colors.colorize("\n\nVerification interrupted by user.", 'orange_red'))
            sys.exit(1)
        
        print("\nVerification Complete!")
        print_summary(results, failed_files, no_md5_files)
        
        sys.exit(1 if results['failed'] else 0)
        
    except KeyboardInterrupt:
        print(colors.colorize("\nOperation cancelled by user.", 'orange_red'))
        sys.exit(1)
    except Exception as e:
        print(colors.colorize(f"\nUnexpected error: {str(e)}", 'orange_red'))
        if os.getenv('DEBUG_FLAC_CHECKER'):
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()