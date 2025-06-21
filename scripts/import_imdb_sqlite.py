#!/usr/bin/env python3
"""
IMDB Data Import Script using SQLite's bulk import functionality.

This script efficiently imports TSV data using SQLite's built-in import capabilities.
It downloads IMDB datasets, decompresses them, and uses a two-stage process:
1. Bulk import raw TSV data into temporary tables
2. Transform and insert data into the final schema with proper types

Features:
- Automatic dataset download
- Efficient bulk import using SQLite's .import command
- Data quality handling (null values, quotes, etc.)
- Progress tracking with colored logging
- Robust error handling with fallback strategies
- Proper foreign key relationships
- SQL queries separated into external files for better maintainability

Usage:
    python3 import_imdb_sqlite.py

Requirements:
    - sqlite3 command-line tool
    - gunzip command
    - Python 3.7+
"""

import sqlite3
import gzip
import os
import sys
import shutil
import urllib.request
import urllib.error
import subprocess
import logging
import argparse
import gc
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import time

# Import SQL queries
from sql_queries import queries

# Configuration
DATA_DIR: str = "data"
DB_PATH: str = os.path.join("traildepot", "data", "main.db")
TEMP_DIR: str = "temp_import"
IMDB_BASE_URL: str = "https://datasets.imdbws.com"

# IMDB file definitions: (gz_filename, temp_table_name)
IMDB_FILES: List[Tuple[str, str]] = [
    ("title.basics.tsv.gz", "t_title_basics"),
    ("name.basics.tsv.gz", "t_name_basics"),
    ("title.ratings.tsv.gz", "t_title_ratings"),
    ("title.episode.tsv.gz", "t_title_episode"),
    ("title.principals.tsv.gz", "t_title_principals"),
    ("title.crew.tsv.gz", "t_title_crew"),
]

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger: logging.Logger = logging.getLogger(__name__)

def check_dependencies() -> None:
    """Check if required commands and modules exist."""
    missing_deps: List[str] = []
    
    # Check for sqlite3 command
    if shutil.which("sqlite3") is None:
        missing_deps.append("sqlite3")
    
    # Check for gunzip command
    if shutil.which("gunzip") is None:
        missing_deps.append("gunzip")
    
    if missing_deps:
        logger.error(f"Missing required dependencies: {', '.join(missing_deps)}")
        logger.info("Please install the missing dependencies and try again.")
        sys.exit(1)

def ensure_data_dir() -> None:
    """Ensure data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

def download_file_with_progress(url: str, local_path: str) -> bool:
    """Download a file with progress indication."""
    filename: str = os.path.basename(local_path)
    logger.info(f"Downloading {filename}...")
    
    try:
        urllib.request.urlretrieve(url, local_path)
        
        size: int = os.path.getsize(local_path)
        logger.info(f"Downloaded {filename} ({size:,} bytes)")
        return True
        
    except urllib.error.URLError as e:
        logger.error(f"Failed to download {filename}: {e}")
        if os.path.exists(local_path):
            os.remove(local_path)
        return False

def download_imdb_datasets() -> None:
    """Download IMDB datasets if they don't exist locally."""
    ensure_data_dir()
    
    files_to_download: List[str] = []
    for gz_filename, _ in IMDB_FILES:
        local_path: str = os.path.join(DATA_DIR, gz_filename)
        if not os.path.exists(local_path):
            files_to_download.append(gz_filename)
        else:
            logger.info(f"Found existing {gz_filename}")
    
    if not files_to_download:
        logger.info("All IMDB datasets already exist locally.")
        return
    
    logger.info(f"Downloading {len(files_to_download)} files from {IMDB_BASE_URL}...")
    logger.warning("Note: These datasets are for non-commercial use only.")
    
    for filename in files_to_download:
        url: str = f"{IMDB_BASE_URL}/{filename}"
        download_path: str = os.path.join(DATA_DIR, filename)
        if not download_file_with_progress(url, download_path):
            sys.exit(1)
    
    logger.info("All downloads completed!")

def ensure_temp_dir() -> None:
    """Ensure temporary directory exists and is clean."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR)

def validate_tsv_file(tsv_path: str) -> bool:
    """Validate TSV file for common issues."""
    filename: str = os.path.basename(tsv_path)
    logger.info(f"Validating {filename}...")
    
    if not os.path.exists(tsv_path):
        logger.error(f"File not found: {tsv_path}")
        return False
    
    file_size: int = os.path.getsize(tsv_path)
    if file_size == 0:
        logger.error(f"File is empty: {tsv_path}")
        return False
    
    # Count lines more efficiently without loading entire file
    line_count: int = 0
    with open(tsv_path, 'r', encoding='utf-8', errors='ignore') as f:
        for _ in f:
            line_count += 1
    logger.info(f"File has {line_count:,} lines")
    
    # Check for quotes (quick sample check) - only read first 100 lines
    quote_lines: int = 0
    with open(tsv_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= 100:  # Only check first 100 lines
                break
            if '"' in line:
                quote_lines += 1
    
    if quote_lines > 0:
        logger.warning(f"Found quotes in {quote_lines} sample lines - will be handled during import")
    
    logger.info(f"Validation completed for {filename}")
    return True

def decompress_file(filename: str, limit: Optional[int] = None) -> str:
    """Decompress a .tsv.gz file to temporary directory."""
    gz_path: str = os.path.join(DATA_DIR, filename)
    tsv_path: str = os.path.join(TEMP_DIR, filename[:-3])  # Remove .gz extension
    
    if not os.path.exists(gz_path):
        logger.error(f"Source file not found: {gz_path}")
        sys.exit(1)
    
    if limit:
        logger.info(f"Decompressing {filename} (limiting to {limit:,} lines)...")
    else:
        logger.info(f"Decompressing {filename}...")
    
    # Use smaller chunks to reduce memory usage
    chunk_size: int = 4096  # Reduced from 8192
    
    with gzip.open(gz_path, 'rt', encoding='utf-8') as f_in:
        with open(tsv_path, 'w', encoding='utf-8') as f_out:
            # Process in smaller chunks to handle large files efficiently
            line_count: int = 0
            for line in f_in:
                f_out.write(line)
                line_count += 1
                
                # Stop if we've reached the limit
                if limit and line_count >= limit:
                    logger.info(f"Reached limit of {limit:,} lines for {filename}")
                    break
    
    file_size: int = os.path.getsize(tsv_path)
    logger.info(f"Decompressed {filename} ({file_size:,} bytes, {line_count:,} lines)")
    return tsv_path

def fix_problematic_quotes(tsv_path: str) -> str:
    """Fix quote handling in TSV data to ensure proper TSV format."""
    fixed_path: str = tsv_path + ".fixed"
    logger.info(f"Fixing quote handling in {os.path.basename(tsv_path)}...")
    
    fixed_fields = 0
    
    with open(tsv_path, 'r', encoding='utf-8', errors='ignore') as f_in:
        with open(fixed_path, 'w', encoding='utf-8') as f_out:
            for line_num, line in enumerate(f_in, 1):
                # Split by tabs to process each field
                fields = line.rstrip('\n').split('\t')
                processed_fields = []
                
                for field in fields:
                    original_field = field
                    
                    # Check if field needs to be quoted (contains tab, newline, or quote)
                    needs_quoting = '\t' in field or '\n' in field or '"' in field
                    
                    if needs_quoting:
                        # If field is already properly quoted (starts and ends with quote)
                        if field.startswith('"') and field.endswith('"'):
                            # Check if internal quotes are properly escaped
                            inner_content = field[1:-1]
                            if '"' in inner_content and '""' not in inner_content:
                                # Escape internal quotes by doubling them
                                inner_content = inner_content.replace('"', '""')
                                field = f'"{inner_content}"'
                                fixed_fields += 1
                        else:
                            # Field needs to be quoted but isn't already
                            # First, escape any existing quotes by doubling them
                            field = field.replace('"', '""')
                            # Then wrap the entire field in quotes
                            field = f'"{field}"'
                            fixed_fields += 1
                    
                    processed_fields.append(field)
                
                f_out.write('\t'.join(processed_fields) + '\n')
                
                # Log progress for large files
                if line_num % 100000 == 0:
                    logger.debug(f"Processed {line_num:,} lines...")
    
    if fixed_fields > 0:
        logger.info(f"Fixed quote handling in {fixed_fields} fields")
    
    return fixed_path

def clean_tsv_for_import(tsv_path: str) -> str:
    """Clean TSV file to handle data quality issues."""
    cleaned_path: str = tsv_path + ".cleaned"
    logger.debug(f"Cleaning {os.path.basename(tsv_path)} for import...")
    
    # First, fix specific problematic patterns
    fixed_path: str = fix_problematic_quotes(tsv_path)
    
    try:
        # Process in chunks to reduce memory usage
        chunk_size: int = 1024 * 1024  # 1MB chunks
        
        with open(fixed_path, 'r', encoding='utf-8', errors='ignore') as f_in:
            with open(cleaned_path, 'w', encoding='utf-8') as f_out:
                while True:
                    chunk: str = f_in.read(chunk_size)
                    if not chunk:
                        break
                    
                    # Process the chunk
                    # Remove carriage returns and null bytes
                    cleaned_chunk: str = chunk.replace('\r', '').replace('\x00', '')
                    
                    # Since fix_problematic_quotes already handled the quote issues,
                    # we just need to do basic cleanup here
                    f_out.write(cleaned_chunk)
        
        return cleaned_path
        
    finally:
        # Clean up the intermediate fixed file
        if os.path.exists(fixed_path):
            os.remove(fixed_path)

def run_sqlite_import(db_path: str, tsv_path: str, table_name: str) -> bool:
    """Run SQLite .import command to bulk import TSV data."""
    filename: str = os.path.basename(tsv_path)
    logger.info(f"Importing {filename} into {table_name}...")
    
    # Clean the TSV file first
    cleaned_tsv_path: str = clean_tsv_for_import(tsv_path)
    
    try:
        # Memory optimization settings based on mode
        cache_size: int = -2000  # 2MB cache
        mmap_size: int = 268435456  # 256MB memory mapping
        
        # Create SQLite commands with memory optimization
        commands: str = f"""
-- Memory optimization settings
PRAGMA cache_size = {cache_size};
PRAGMA temp_store = 2;      -- Store temp tables in memory
PRAGMA mmap_size = {mmap_size};
PRAGMA synchronous = NORMAL;   -- Faster writes, still safe
PRAGMA journal_mode = WAL;     -- Write-ahead logging for better performance

.mode tabs
.headers on
.separator "\\t"
.import {cleaned_tsv_path} {table_name}
"""
        
        # Run sqlite3 with the commands
        process: subprocess.CompletedProcess = subprocess.run(
            ['sqlite3', db_path],
            input=commands,
            text=True,
            capture_output=True
        )
        
        if process.returncode == 0:
            logger.info(f"Successfully imported {table_name}")
            return True
        else:
            logger.error(f"Error importing {table_name}: {process.stderr}")
            
            # Try alternative CSV mode with memory optimization
            logger.info("Attempting alternative import method...")
            csv_commands: str = f"""
-- Memory optimization settings
PRAGMA cache_size = {cache_size};
PRAGMA temp_store = 2;
PRAGMA mmap_size = {mmap_size};
PRAGMA synchronous = NORMAL;
PRAGMA journal_mode = WAL;

.mode csv
.separator "\\t"
.import {cleaned_tsv_path} {table_name}
"""
            
            process = subprocess.run(
                ['sqlite3', db_path],
                input=csv_commands,
                text=True,
                capture_output=True
            )
            
            if process.returncode == 0:
                logger.info(f"Successfully imported {table_name} using CSV mode")
                return True
            else:
                logger.error(f"Failed to import {table_name}: {process.stderr}")
                return False
    
    finally:
        # Clean up the temporary cleaned file
        if os.path.exists(cleaned_tsv_path):
            os.remove(cleaned_tsv_path)

def run_sqlite_import_optimized(db_path: str, tsv_path: str, table_name: str, skip_clean: bool = True, low_memory: bool = True) -> bool:
    """Run SQLite .import command to bulk import TSV data with memory optimization."""
    filename: str = os.path.basename(tsv_path)
    logger.info(f"Importing {filename} into {table_name}...")
    
    # Use original file if cleaning is skipped
    import_path: str = tsv_path
    if not skip_clean:
        import_path = clean_tsv_for_import(tsv_path)
    
    try:
        # Memory optimization settings based on mode
        if low_memory:
            cache_size: int = -1000  # 1MB cache
            mmap_size: int = 67108864  # 64MB memory mapping
        else:
            cache_size = -2000  # 2MB cache
            mmap_size = 268435456  # 256MB memory mapping
        
        # Create SQLite commands with memory optimization
        commands: str = f"""
-- Memory optimization settings
PRAGMA cache_size = {cache_size};
PRAGMA temp_store = 2;      -- Store temp tables in memory
PRAGMA mmap_size = {mmap_size};
PRAGMA synchronous = NORMAL;   -- Faster writes, still safe
PRAGMA journal_mode = WAL;     -- Write-ahead logging for better performance

.mode tabs
.headers on
.separator "\\t"
.import {import_path} {table_name}
"""
        
        # Run sqlite3 with the commands
        process: subprocess.CompletedProcess = subprocess.run(
            ['sqlite3', db_path],
            input=commands,
            text=True,
            capture_output=True
        )
        
        if process.returncode == 0:
            # Verify the import was successful by checking row count
            verify_commands: str = f"SELECT COUNT(*) FROM {table_name};"
            verify_process: subprocess.CompletedProcess = subprocess.run(
                ['sqlite3', db_path],
                input=verify_commands,
                text=True,
                capture_output=True
            )
            
            if verify_process.returncode == 0:
                row_count: str = verify_process.stdout.strip()
                logger.info(f"Successfully imported {table_name} ({row_count} rows)")
                return True
            else:
                logger.warning(f"Import verification failed for {table_name}")
                return True  # Still consider it successful if import completed
        
        else:
            logger.error(f"Error importing {table_name}: {process.stderr}")
            
            # Try alternative CSV mode with memory optimization
            logger.info("Attempting alternative import method...")
            csv_commands: str = f"""
-- Memory optimization settings
PRAGMA cache_size = {cache_size};
PRAGMA temp_store = 2;
PRAGMA mmap_size = {mmap_size};
PRAGMA synchronous = NORMAL;
PRAGMA journal_mode = WAL;

.mode csv
.separator "\\t"
.import {import_path} {table_name}
"""
            
            process = subprocess.run(
                ['sqlite3', db_path],
                input=csv_commands,
                text=True,
                capture_output=True
            )
            
            if process.returncode == 0:
                # Verify the import was successful
                verify_commands = f"SELECT COUNT(*) FROM {table_name};"
                verify_process = subprocess.run(
                    ['sqlite3', db_path],
                    input=verify_commands,
                    text=True,
                    capture_output=True
                )
                
                if verify_process.returncode == 0:
                    row_count = verify_process.stdout.strip()
                    logger.info(f"Successfully imported {table_name} using CSV mode ({row_count} rows)")
                    return True
                else:
                    logger.warning(f"Import verification failed for {table_name}")
                    return True
            
            # If both methods fail, try Python-based import as last resort
            logger.warning("SQLite import methods failed, attempting Python-based import...")
            return import_with_python(db_path, import_path, table_name)
    
    finally:
        # Clean up the temporary cleaned file if we created one
        if not skip_clean and os.path.exists(import_path) and import_path != tsv_path:
            os.remove(import_path)

def import_with_python(db_path: str, tsv_path: str, table_name: str) -> bool:
    """Fallback method: Import TSV using Python csv module."""
    logger.info(f"Using Python CSV import for {table_name}...")
    
    try:
        import csv
        
        # Connect to database
        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cursor: sqlite3.Cursor = conn.cursor()
        
        # Clear existing data
        cursor.execute(f"DELETE FROM {table_name}")
        
        # Read TSV file and insert rows
        row_count: int = 0
        with open(tsv_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Skip header row
            next(f)
            
            tsv_reader = csv.reader(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            
            for row in tsv_reader:
                # Handle missing fields by padding with None
                while len(row) < 10:  # Most IMDB tables have <= 10 columns
                    row.append(None)
                
                # Create placeholders for the insert
                placeholders = ','.join(['?' for _ in row])
                insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                
                try:
                    cursor.execute(insert_sql, row)
                    row_count += 1
                    
                    # Commit every 10000 rows to avoid memory issues
                    if row_count % 10000 == 0:
                        conn.commit()
                        logger.debug(f"Imported {row_count:,} rows...")
                        
                except sqlite3.Error as e:
                    logger.warning(f"Skipping problematic row {row_count + 1}: {e}")
                    continue
        
        conn.commit()
        conn.close()
        
        logger.info(f"Successfully imported {table_name} using Python ({row_count:,} rows)")
        return True
        
    except Exception as e:
        logger.error(f"Python import failed for {table_name}: {e}")
        return False

def create_temp_tables(conn: sqlite3.Connection) -> None:
    """Create temporary tables that match the TSV structure."""
    logger.info("Creating temporary tables...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Drop existing temp tables
    for _, temp_table in IMDB_FILES:
        cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
    
    # Load and execute SQL from file
    cursor.executescript(queries.temp_tables)
    
    conn.commit()
    logger.info("Created temporary tables")

def import_titles(conn: sqlite3.Connection) -> None:
    """Import titles from temp table to final table."""
    logger.info("Processing titles...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Load and execute SQL from file
    cursor.execute(queries.import_titles)
    
    count: int = cursor.execute("SELECT COUNT(*) FROM titles").fetchone()[0]
    conn.commit()
    logger.info(f"Processed {count:,} titles")

def import_persons(conn: sqlite3.Connection) -> None:
    """Import persons from temp table to final table."""
    logger.info("Processing persons...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Load and execute SQL from file
    cursor.execute(queries.import_persons)
    
    count: int = cursor.execute("SELECT COUNT(*) FROM persons").fetchone()[0]
    conn.commit()
    logger.info(f"Processed {count:,} persons")

def import_ratings(conn: sqlite3.Connection) -> None:
    """Import ratings from temp table to final table."""
    logger.info("Processing ratings...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Load and execute SQL from file
    cursor.execute(queries.import_ratings)
    
    count: int = cursor.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
    conn.commit()
    logger.info(f"Processed {count:,} ratings")

def import_episodes(conn: sqlite3.Connection) -> None:
    """Import episodes from temp table to final table."""
    logger.info("Processing episodes...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Load and execute SQL from file
    cursor.execute(queries.import_episodes)
    
    count: int = cursor.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    conn.commit()
    logger.info(f"Processed {count:,} episodes")

def import_principals(conn: sqlite3.Connection) -> None:
    """Import principals from temp table to final table."""
    logger.info("Processing principals...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Load and execute SQL from file
    cursor.execute(queries.import_principals)
    
    count: int = cursor.execute("SELECT COUNT(*) FROM principals").fetchone()[0]
    conn.commit()
    logger.info(f"Processed {count:,} principals")

def import_crew(conn: sqlite3.Connection) -> None:
    """Import crew from temp table to final table."""
    logger.info("Processing crew...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    
    # Handle directors - split comma-separated values
    logger.info("Processing directors...")
    cursor.execute(queries.import_crew_directors)
    
    # Handle writers - split comma-separated values
    logger.info("Processing writers...")
    cursor.execute(queries.import_crew_writers)
    
    count: int = cursor.execute("SELECT COUNT(*) FROM crew").fetchone()[0]
    conn.commit()
    logger.info(f"Processed {count:,} crew members")

def cleanup_temp_tables(conn: sqlite3.Connection) -> None:
    """Clean up temporary tables."""
    logger.info("Cleaning up temporary tables...")
    
    cursor: sqlite3.Cursor = conn.cursor()
    for _, temp_table in IMDB_FILES:
        cursor.execute(f"DROP TABLE IF EXISTS {temp_table}")
    
    conn.commit()
    logger.info("Cleaned up temporary tables")

def validate_import_quality(db_path: str, table_name: str) -> bool:
    """Validate the quality of imported data."""
    logger.info(f"Validating import quality for {table_name}...")
    
    try:
        conn: sqlite3.Connection = sqlite3.connect(db_path)
        cursor: sqlite3.Cursor = conn.cursor()
        
        # Get total row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows: int = cursor.fetchone()[0]
        
        if total_rows == 0:
            logger.error(f"No data imported into {table_name}")
            conn.close()
            return False
        
        # Check for common data quality issues
        issues_found: int = 0
        
        # Check for rows with too many NULL values (might indicate parsing issues)
        if table_name == "t_title_principals":
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE tconst IS NULL OR nconst IS NULL OR category IS NULL
            """)
            null_issues = cursor.fetchone()[0]
            if null_issues > 0:
                logger.warning(f"Found {null_issues} rows with NULL values in key fields")
                issues_found += null_issues
        
        # Check for malformed data in specific tables
        if table_name == "t_title_principals":
            # Check for characters field with unescaped quotes
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_name} 
                WHERE characters LIKE '%"%' AND characters NOT LIKE '"%"%'
            """)
            quote_issues = cursor.fetchone()[0]
            if quote_issues > 0:
                logger.warning(f"Found {quote_issues} rows with potential quote issues in characters field")
                issues_found += quote_issues
        
        conn.close()
        
        if issues_found > 0:
            logger.warning(f"Found {issues_found} potential data quality issues in {table_name}")
            return False
        else:
            logger.info(f"Data quality validation passed for {table_name} ({total_rows:,} rows)")
            return True
            
    except Exception as e:
        logger.error(f"Error validating {table_name}: {e}")
        return False

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Import IMDB datasets into SQLite database using bulk import (optimized for memory usage)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Import with optimized memory settings (default)
  %(prog)s --verbose          # Enable debug logging
  %(prog)s --data-dir ./data  # Use custom data directory
  %(prog)s --clean            # Enable TSV cleaning step (uses more memory, default: enabled)
  %(prog)s --high-memory      # Use high memory settings (faster but uses more RAM, default: low memory)
  %(prog)s --limit 1000       # Import only first 1000 entries per file (for testing)
        """
    )
    
    parser.add_argument(
        "--data-dir",
        default=DATA_DIR,
        help=f"Directory to store downloaded datasets (default: {DATA_DIR})"
    )
    
    parser.add_argument(
        "--db-path",
        default=DB_PATH,
        help=f"Path to SQLite database (default: {DB_PATH})"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose (debug) logging"
    )
    
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip downloading datasets (use existing files)"
    )
    
    parser.add_argument(
        "--clean",
        action="store_true",
        default=True,  # Enable cleaning by default
        help="Enable TSV cleaning step (uses more memory, default: enabled)"
    )
    
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Disable TSV cleaning step (faster but may have data quality issues)"
    )
    
    parser.add_argument(
        "--high-memory",
        action="store_true",
        help="Use high memory settings (faster but uses more RAM, default: low memory)"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        metavar="N",
        help="Import only first N entries per file (useful for testing with smaller datasets)"
    )
    
    return parser.parse_args()

def main() -> None:
    """Main function."""
    args: argparse.Namespace = parse_args()
    
    # Update global configuration based on arguments
    global DATA_DIR, DB_PATH
    DATA_DIR = args.data_dir
    DB_PATH = args.db_path
    
    # Adjust logging level if verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    logger.info("IMDB Data Import Script (Python)")
    logger.info("=" * 50)
    logger.info(f"Data directory: {DATA_DIR}")
    logger.info(f"Database path: {DB_PATH}")
    if args.no_clean:
        logger.info("TSV cleaning disabled")
    else:
        logger.info("TSV cleaning enabled (default)")
    if args.high_memory:
        logger.info("High memory mode enabled")
    else:
        logger.info("Low memory mode enabled (default)")
    
    if args.limit:
        logger.info(f"Import limit: {args.limit:,} entries per file")
    
    start_time: float = time.time()
    
    # Check dependencies
    check_dependencies()
    
    # Download datasets if needed
    if not args.skip_download:
        download_imdb_datasets()
    else:
        logger.info("Skipping dataset download as requested")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file not found at {DB_PATH}")
        logger.info("Please run the TrailBase server once to create the database, then stop it and run this script.")
        sys.exit(1)
    
    ensure_temp_dir()
    
    try:
        # Decompress all files
        decompressed_files: Dict[str, str] = {}
        for gz_filename, temp_table in IMDB_FILES:
            tsv_path: str = decompress_file(gz_filename, args.limit)
            decompressed_files[temp_table] = tsv_path
        
        # Create temporary tables first
        with sqlite3.connect(DB_PATH) as conn:
            create_temp_tables(conn)
        
        # Import each file with validation
        import_success: bool = True
        for gz_filename, temp_table in IMDB_FILES:
            current_tsv_path: str = decompressed_files[temp_table]
            skip_clean: bool = args.no_clean  # Skip cleaning if --no-clean is specified
            low_memory: bool = not args.high_memory  # Default to True (low memory)
            
            if not run_sqlite_import_optimized(DB_PATH, current_tsv_path, temp_table, skip_clean, low_memory):
                logger.error(f"Failed to import {gz_filename}")
                import_success = False
                break
            
            # Validate import quality
            if not validate_import_quality(DB_PATH, temp_table):
                logger.warning(f"Data quality issues detected in {temp_table}")
                # Continue with import but log the warning
            
            # Force garbage collection after each import to free memory
            gc.collect()
        
        if not import_success:
            logger.error("Import failed, stopping processing")
            sys.exit(1)
        
        # Process the data in the correct order
        with sqlite3.connect(DB_PATH) as conn:
            # Import in dependency order
            import_titles(conn)
            import_persons(conn)
            import_ratings(conn)
            import_episodes(conn)
            import_principals(conn)
            import_crew(conn)
            
            cleanup_temp_tables(conn)
        
        elapsed_time: float = time.time() - start_time
        logger.info(f"Import completed successfully in {elapsed_time:.1f} seconds!")
        
    finally:
        # Clean up temporary directory
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR)
            logger.info("Cleaned up temporary files")

if __name__ == "__main__":
    main()
