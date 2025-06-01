#!/usr/bin/env python3
import os
import sys
import subprocess
import multiprocessing
import argparse
import threading
from concurrent.futures import ThreadPoolExecutor
import math
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

class ProgressTracker:
    def __init__(self, total):
        self.total = total
        self.progress = 0
        self.success = 0
        self.failed = 0
        self.lock = threading.Lock()
        self.errors = []

    def update(self, success, error_info=None):
        """Update progress and display the status bar"""
        with self.lock:
            self.progress += 1
            if success:
                self.success += 1
            else:
                self.failed += 1
                if error_info:
                    self.errors.append(error_info)
            
            # Create status bar with aligned elements
            width = 50
            filled = int(width * self.progress / self.total)
            bar = '#' * filled + ' ' * (width - filled)
            percent = f"{int(100 * self.progress / self.total):3d}"  # 3-digit percentage
            progress_str = f"{self.progress:>{len(str(self.total))}}/{self.total}"  # Aligned progress
            success_text = f"{Fore.GREEN}Success: {self.success:<4}{Style.RESET_ALL}"
            failed_text = f"{Fore.RED}Failed: {self.failed:<4}{Style.RESET_ALL}"
            status = f"[{bar}] {percent}% ({progress_str}) | {success_text} | {failed_text}"
            
            sys.stdout.write(f"\r{status}")
            sys.stdout.flush()
            
            if self.progress == self.total:
                print("\n")  # Extra newline for separation

def recompress_flac(file_path, tracker, compression_level):
    """Recompress a FLAC file using the specified compression level"""
    try:
        # Check if FLAC is installed
        subprocess.run(["flac", "--version"], capture_output=True, check=True)
        
        subprocess.run(
            ["flac", f"-{compression_level}", "-f", str(file_path)],
            capture_output=True,
            check=True
        )
        tracker.update(True)
        return True
    except FileNotFoundError:
        tracker.update(False, "The FLAC tool is not installed. Please install 'flac' to proceed.")
        return False
    except subprocess.CalledProcessError as e:
        error_msg = f"Failed to process {Fore.RED}{file_path}{Style.RESET_ALL}:\n"
        # Filter out version and copyright lines
        lines = e.stderr.decode().split('\n')
        filtered_lines = [line for line in lines 
                         if "Copyright" not in line 
                         and "NO WARRANTY" not in line 
                         and "Type `flac'" not in line 
                         and not line.strip().startswith("flac ")]
        # Clean up and format error output
        for i, line in enumerate(filtered_lines):
            if line.strip() and os.path.basename(file_path) in line and i == 0:
                # Skip redundant filename line if it's the first meaningful line
                continue
            if line.strip():
                error_msg += f"  {line}\n"  # Indent all error details
        tracker.update(False, error_msg)
        return False
    except Exception as e:
        tracker.update(False, f"Unexpected issue with {file_path}: {str(e)}")
        return False

def clean_path(path):
    """Normalize the provided file path"""
    path = path.strip("'\"")
    return os.path.normpath(path)

def main():
    """Recompress all FLAC files in the specified directory"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Recompress FLAC files with a chosen compression level')
    parser.add_argument('-d', '--directory', default=os.getcwd(), 
                       help='Directory to search for FLAC files (default: current directory)')
    parser.add_argument('-c', '--compression', type=int, default=5, choices=range(0, 9), 
                       help='Compression level from 0 to 8 (default: 5)')
    args = parser.parse_args()

    # Calculate thread count (75% of available CPU threads)
    max_threads = max(1, math.floor(multiprocessing.cpu_count() * 0.75))

    # Validate directory
    directory = clean_path(args.directory)
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory.")
        return

    # Locate FLAC files
    flac_files = [os.path.join(root, file) 
                 for root, _, files in os.walk(directory) 
                 for file in files if file.lower().endswith('.flac')]

    if not flac_files:
        print("No FLAC files were found in the specified directory.")
        return

    # Display configuration and ask for confirmation
    print(f"\nDirectory scanned: {directory}")
    print(f"Files found: {len(flac_files)}")
    print(f"Compression level: {args.compression}")
    print(f"Threads to use: {max_threads}")
    print()  # Spacing before prompt
    
    response = input("Start the re-encoding process? (Y/n): ").strip().lower()
    if response not in ('y', ''):
        print("Process aborted by user.")
        return
    
    print()  # Spacing before progress
    print(f"Processing with compression level {args.compression} using {max_threads} threads.")

    # Start processing
    tracker = ProgressTracker(len(flac_files))
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = [executor.submit(recompress_flac, file_path, tracker, args.compression) 
                  for file_path in flac_files]
        for future in futures:
            future.result()

    # Completion message
    print("Recompression process finished.")

    # Display errors if any
    if tracker.errors:
        print("\nEncountered the following issues:")
        print("-" * 70)
        for error in tracker.errors:
            print(error.strip())
            print("-" * 70)

if __name__ == "__main__":
    main()