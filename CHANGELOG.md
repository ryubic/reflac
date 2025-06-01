# FLAC Integrity Checker Changelog

## Version 1.4 (June 1, 2025)
- **Enhancements:**
  - Renamed the file from FIC.py to fic.py so the user doesn't have to capitalize the first letter for auto complete to work in some shells
- **Code Quality Improvements:**
  - Removed the unnecessery import of datetime module
  - Thats all, and dont ask why the version number is 1.4 haha

## Version 1.2.2 (April 08, 2025)
- **Enhancements:**
  - Added command-line options `--max-threads`, `--timeout`, and `--max-retries` to make thread count, verification timeout, and retry attempts configurable (previously hardcoded).
  - Implemented thread-safe logging using `QueueHandler` and `QueueListener` to prevent potential race conditions in multi-threaded execution.
  - Added a warning in verbose mode if the `tqdm` library is unavailable, improving user experience by clarifying missing progress bar functionality.
  - Replaced global `colors` object with function parameter passing for better encapsulation and testability.

- **Bug Fixes:**
  - Fixed `UnicodeDecodeError` on Windows by explicitly setting `encoding='utf-8'` with `errors='replace'` in `run_command`, ensuring robust handling of non-ASCII output from `flac` and `metaflac`.
  - Simplified datetime usage by changing `datetime.datetime.now()` to `datetime.now()` with an updated import (`from datetime import datetime`).

- **Code Quality Improvements:**
  - Removed redundant `logging.getLogger().isEnabledFor()` checks, relying on the logging framework’s internal level filtering for cleaner and slightly faster code.
  - Replaced broad `except Exception` clauses with specific exceptions (e.g., `OSError`, `subprocess.SubprocessError`) for better error handling and debugging.
  - Optimized `clean_flac_error` with an early return for empty or whitespace-only strings, reducing unnecessary processing.
  - Enhanced `normalize_path` with input validation to handle invalid or empty path inputs gracefully.
  - Removed undocumented `DEBUG_FLAC_CHECKER` environment variable check, using the `--verbose` flag consistently for debug output.

- **Documentation:**
  - Updated usage instructions in the script’s docstring to reflect new command-line options.
  - Improved code maintainability and readability with consistent parameter passing and specific exception handling.

## Version 1.2.1 (March 31, 2025)
Changes:
- Enhanced file reporting and path handling
- Added detailed file type statistics to show counts of non-FLAC files (mp3, wav, etc.)
- Fixed path handling issues with directory paths containing spaces
- Improved detection and display of different media file types organized by category
- Fixed forward/backslash issues in path normalization across different operating systems
- Enhanced error messages for path-related problems with examples of correct usage
- Added better timeout handling for FLAC verification operations
- Improved the retry mechanism for intermittent file access issues
- Updated documentation to reflect new features and usage examples