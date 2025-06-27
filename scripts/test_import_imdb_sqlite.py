#!/usr/bin/env python3
"""
Test suite for IMDB import script.

This module provides comprehensive tests for the import functionality,
including unit tests, integration tests, and performance tests.
"""

import unittest
import tempfile
import os
import sqlite3
import gzip
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from typing import List, Dict, Any

# Import the functions to test
from import_imdb_sqlite import (
    check_dependencies,
    ensure_data_dir,
    download_file_with_progress,
    validate_tsv_file,
    clean_tsv_for_import,
    decompress_file,
    create_temp_tables,
    import_titles,
    import_persons,
    import_ratings,
    import_episodes,
    import_principals,
    import_crew,
    cleanup_temp_tables,
    parse_args,
    IMDB_FILES,
    DATA_DIR,
    TEMP_DIR
)

class TestImportIMDBSQLite(unittest.TestCase):
    """Test cases for IMDB import functionality."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_data_dir = os.path.join(self.temp_dir, "data")
        self.test_temp_dir = os.path.join(self.temp_dir, "temp")
        self.test_db_path = os.path.join(self.temp_dir, "test.db")
        
        # Create test directories
        os.makedirs(self.test_data_dir, exist_ok=True)
        os.makedirs(self.test_temp_dir, exist_ok=True)
        
        # Create a test database
        self.create_test_database()
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_database(self) -> None:
        """Create a test database with basic schema."""
        conn = sqlite3.connect(self.test_db_path)
        cursor = conn.cursor()
        
        # Create basic tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS titles (
                id TEXT PRIMARY KEY,
                title TEXT,
                type TEXT,
                year INTEGER,
                runtime INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS persons (
                id TEXT PRIMARY KEY,
                name TEXT,
                birth_year INTEGER,
                death_year INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS ratings (
                title_id TEXT PRIMARY KEY,
                rating REAL,
                votes INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS episodes (
                id TEXT PRIMARY KEY,
                parent_id TEXT,
                season INTEGER,
                episode INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS principals (
                id TEXT PRIMARY KEY,
                title_id TEXT,
                person_id TEXT,
                category TEXT,
                job TEXT
            );
            
            CREATE TABLE IF NOT EXISTS crew (
                id TEXT PRIMARY KEY,
                title_id TEXT,
                person_id TEXT,
                category TEXT
            );
        """)
        
        conn.commit()
        conn.close()
    
    def create_test_tsv_file(self, filename: str, content: str) -> str:
        """Create a test TSV file."""
        filepath = os.path.join(self.test_data_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def create_test_gz_file(self, filename: str, content: str) -> str:
        """Create a test gzipped TSV file."""
        filepath = os.path.join(self.test_data_dir, filename)
        with gzip.open(filepath, 'wt', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def test_check_dependencies(self) -> None:
        """Test dependency checking."""
        # This should not raise an exception if sqlite3 and gunzip are available
        try:
            check_dependencies()
        except SystemExit:
            self.fail("check_dependencies() raised SystemExit unexpectedly")
    
    def test_ensure_data_dir(self) -> None:
        """Test data directory creation."""
        test_dir = os.path.join(self.temp_dir, "test_data")
        with patch('import_imdb_sqlite.DATA_DIR', test_dir):
            ensure_data_dir()
            self.assertTrue(os.path.exists(test_dir))
    
    @patch('urllib.request.urlretrieve')
    def test_download_file_with_progress_success(self, mock_urlretrieve: MagicMock) -> None:
        """Test successful file download."""
        test_file = os.path.join(self.temp_dir, "test.txt")
        
        # Mock successful download
        mock_urlretrieve.return_value = None
        
        result = download_file_with_progress("http://example.com/test.txt", test_file)
        self.assertTrue(result)
        mock_urlretrieve.assert_called_once()
    
    @patch('urllib.request.urlretrieve')
    def test_download_file_with_progress_failure(self, mock_urlretrieve: MagicMock) -> None:
        """Test failed file download."""
        test_file = os.path.join(self.temp_dir, "test.txt")
        
        # Mock failed download
        mock_urlretrieve.side_effect = Exception("Download failed")
        
        result = download_file_with_progress("http://example.com/test.txt", test_file)
        self.assertFalse(result)
    
    def test_validate_tsv_file_valid(self) -> None:
        """Test TSV file validation with valid file."""
        content = "id\ttitle\ttype\tyear\truntime\n"
        content += "tt0000001\tTest Movie\tmovie\t2020\t120\n"
        content += "tt0000002\tTest Show\ttvSeries\t2021\t45\n"
        
        filepath = self.create_test_tsv_file("test.tsv", content)
        result = validate_tsv_file(filepath)
        self.assertTrue(result)
    
    def test_validate_tsv_file_empty(self) -> None:
        """Test TSV file validation with empty file."""
        filepath = self.create_test_tsv_file("empty.tsv", "")
        result = validate_tsv_file(filepath)
        self.assertFalse(result)
    
    def test_validate_tsv_file_not_found(self) -> None:
        """Test TSV file validation with non-existent file."""
        result = validate_tsv_file("/nonexistent/file.tsv")
        self.assertFalse(result)
    
    def test_clean_tsv_for_import(self) -> None:
        """Test TSV cleaning functionality."""
        content = 'id\ttitle\ttype\n'
        content += 'tt0000001\t"Test Movie"\tmovie\n'
        content += 'tt0000002\tTest\rShow\ttvSeries\n'
        
        filepath = self.create_test_tsv_file("test.tsv", content)
        cleaned_path = clean_tsv_for_import(filepath)
        
        # Check that cleaned file exists
        self.assertTrue(os.path.exists(cleaned_path))
        
        # Check that quotes are escaped and carriage returns are removed
        with open(cleaned_path, 'r', encoding='utf-8') as f:
            cleaned_content = f.read()
        
        self.assertIn('""Test Movie""', cleaned_content)  # Quotes should be escaped
        self.assertNotIn('\r', cleaned_content)  # Carriage returns should be removed
        
        # Clean up
        os.remove(cleaned_path)
    
    def test_decompress_file(self) -> None:
        """Test file decompression."""
        content = "id\ttitle\ttype\n"
        content += "tt0000001\tTest Movie\tmovie\n"
        
        gz_filepath = self.create_test_gz_file("test.tsv.gz", content)
        
        with patch('import_imdb_sqlite.TEMP_DIR', self.test_temp_dir):
            with patch('import_imdb_sqlite.DATA_DIR', self.test_data_dir):
                result = decompress_file("test.tsv.gz")
        
        # Check that decompressed file exists
        self.assertTrue(os.path.exists(result))
        
        # Check content
        with open(result, 'r', encoding='utf-8') as f:
            decompressed_content = f.read()
        
        self.assertEqual(content, decompressed_content)
    
    def test_create_temp_tables(self) -> None:
        """Test temporary table creation."""
        conn = sqlite3.connect(self.test_db_path)
        
        try:
            create_temp_tables(conn)
            
            # Check that temp tables were created
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 't_%'")
            temp_tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = [table for _, table in IMDB_FILES]
            for table in expected_tables:
                self.assertIn(table, temp_tables)
        
        finally:
            conn.close()
    
    def test_import_functions(self) -> None:
        """Test import functions with sample data."""
        conn = sqlite3.connect(self.test_db_path)
        
        try:
            # Create temp tables first
            create_temp_tables(conn)
            
            # Insert some test data into temp tables
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO t_title_basics (tconst, titleType, primaryTitle, startYear, runtimeMinutes)
                VALUES ('tt0000001', 'movie', 'Test Movie', '2020', '120')
            """)
            
            cursor.execute("""
                INSERT INTO t_name_basics (nconst, primaryName, birthYear, deathYear)
                VALUES ('nm0000001', 'Test Actor', '1980', NULL)
            """)
            
            conn.commit()
            
            # Test import functions
            import_titles(conn)
            import_persons(conn)
            
            # Check that data was imported
            cursor.execute("SELECT COUNT(*) FROM titles")
            title_count = cursor.fetchone()[0]
            self.assertEqual(title_count, 1)
            
            cursor.execute("SELECT COUNT(*) FROM persons")
            person_count = cursor.fetchone()[0]
            self.assertEqual(person_count, 1)
        
        finally:
            conn.close()
    
    def test_cleanup_temp_tables(self) -> None:
        """Test temporary table cleanup."""
        conn = sqlite3.connect(self.test_db_path)
        
        try:
            # Create temp tables
            create_temp_tables(conn)
            
            # Verify they exist
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 't_%'")
            temp_tables_before = [row[0] for row in cursor.fetchall()]
            self.assertGreater(len(temp_tables_before), 0)
            
            # Clean up
            cleanup_temp_tables(conn)
            
            # Verify they're gone
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 't_%'")
            temp_tables_after = [row[0] for row in cursor.fetchall()]
            self.assertEqual(len(temp_tables_after), 0)
        
        finally:
            conn.close()
    
    def test_parse_args_default(self) -> None:
        """Test argument parsing with default values."""
        with patch('sys.argv', ['import_imdb_sqlite.py']):
            args = parse_args()
            self.assertEqual(args.data_dir, DATA_DIR)
            self.assertFalse(args.verbose)
            self.assertFalse(args.skip_download)
            self.assertFalse(args.skip_clean)
            self.assertFalse(args.low_memory)
    
    def test_parse_args_custom(self) -> None:
        """Test argument parsing with custom values."""
        with patch('sys.argv', [
            'import_imdb_sqlite.py',
            '--data-dir', '/custom/data',
            '--verbose',
            '--skip-download',
            '--skip-clean',
            '--low-memory'
        ]):
            args = parse_args()
            self.assertEqual(args.data_dir, '/custom/data')
            self.assertTrue(args.verbose)
            self.assertTrue(args.skip_download)
            self.assertTrue(args.skip_clean)
            self.assertTrue(args.low_memory)

class TestSQLQueries(unittest.TestCase):
    """Test cases for SQL queries module."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_sql_dir = os.path.join(self.temp_dir, "sql")
        os.makedirs(self.test_sql_dir, exist_ok=True)
    
    def tearDown(self) -> None:
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_sql_file(self, filename: str, content: str) -> str:
        """Create a test SQL file."""
        filepath = os.path.join(self.test_sql_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return filepath
    
    def test_sql_queries_load(self) -> None:
        """Test SQL queries loading."""
        from sql_queries import SQLQueries
        
        # Create test SQL file
        sql_content = "CREATE TABLE test (id INTEGER PRIMARY KEY);"
        self.create_test_sql_file("test.sql", sql_content)
        
        # Test loading
        queries = SQLQueries(self.test_sql_dir)
        result = queries.load("test.sql")
        self.assertEqual(result, sql_content)
    
    def test_sql_queries_load_missing_file(self) -> None:
        """Test SQL queries loading with missing file."""
        from sql_queries import SQLQueries
        
        queries = SQLQueries(self.test_sql_dir)
        with self.assertRaises(FileNotFoundError):
            queries.load("nonexistent.sql")

def run_performance_tests() -> None:
    """Run performance tests."""
    print("\n" + "="*50)
    print("PERFORMANCE TESTS")
    print("="*50)
    
    # Test file processing performance
    import time
    
    # Create a large test file
    temp_dir = tempfile.mkdtemp()
    test_file = os.path.join(temp_dir, "large_test.tsv")
    
    try:
        # Create a 1MB test file
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("id\ttitle\ttype\n")
            for i in range(10000):
                f.write(f"tt{i:07d}\tTest Movie {i}\tmovie\n")
        
        # Test validation performance
        start_time = time.time()
        result = validate_tsv_file(test_file)
        validation_time = time.time() - start_time
        
        print(f"Validation performance: {validation_time:.3f}s for 1MB file")
        self.assertTrue(result)
        
        # Test cleaning performance
        start_time = time.time()
        cleaned_file = clean_tsv_for_import(test_file)
        cleaning_time = time.time() - start_time
        
        print(f"Cleaning performance: {cleaning_time:.3f}s for 1MB file")
        self.assertTrue(os.path.exists(cleaned_file))
        
        # Clean up
        os.remove(cleaned_file)
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    # Run unit tests
    unittest.main(verbosity=2, exit=False)
    
    # Run performance tests
    run_performance_tests() 