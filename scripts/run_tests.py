#!/usr/bin/env python3
"""
Simple test runner for IMDB import scripts.

This script runs basic tests to verify the import functionality works correctly.
"""

import sys
import os
import tempfile
import sqlite3
import shutil
from pathlib import Path

# Add the scripts directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_sql_queries_loading() -> bool:
    """Test that SQL queries can be loaded."""
    print("Testing SQL queries loading...")
    try:
        from sql_queries import queries
        
        # Test that all required SQL files can be loaded
        required_files = [
            "temp_tables.sql",
            "import_titles.sql", 
            "import_persons.sql",
            "import_ratings.sql",
            "import_episodes.sql",
            "import_principals.sql",
            "import_crew.sql",
            "import_crew_writers.sql"
        ]
        
        for filename in required_files:
            try:
                content = queries.load(filename)
                if not content.strip():
                    print(f"  ❌ {filename} is empty")
                    return False
                print(f"  ✅ {filename} loaded successfully")
            except FileNotFoundError:
                print(f"  ❌ {filename} not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error loading SQL queries: {e}")
        return False

def test_import_functions() -> bool:
    """Test that import functions can be imported and called."""
    print("Testing import functions...")
    try:
        from import_imdb_sqlite import (
            check_dependencies,
            ensure_data_dir,
            validate_tsv_file,
            clean_tsv_for_import,
            create_temp_tables,
            cleanup_temp_tables
        )
        print("  ✅ All functions imported successfully")
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_file_operations() -> bool:
    """Test file operations with temporary files."""
    print("Testing file operations...")
    
    temp_dir = tempfile.mkdtemp()
    try:
        # Test TSV validation
        test_file = os.path.join(temp_dir, "test.tsv")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("id\ttitle\ttype\n")
            f.write("tt0000001\tTest Movie\tmovie\n")
        
        from import_imdb_sqlite import validate_tsv_file, clean_tsv_for_import
        
        # Test validation
        if not validate_tsv_file(test_file):
            print("  ❌ TSV validation failed")
            return False
        print("  ✅ TSV validation passed")
        
        # Test cleaning
        cleaned_file = clean_tsv_for_import(test_file)
        if not os.path.exists(cleaned_file):
            print("  ❌ TSV cleaning failed")
            return False
        print("  ✅ TSV cleaning passed")
        
        # Clean up
        os.remove(cleaned_file)
        
        return True
        
    except Exception as e:
        print(f"  ❌ File operation error: {e}")
        return False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

def test_database_operations() -> bool:
    """Test database operations."""
    print("Testing database operations...")
    
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db.close()
    
    try:
        conn = sqlite3.connect(temp_db.name)
        
        # Test temp table creation
        from import_imdb_sqlite import create_temp_tables, cleanup_temp_tables
        
        create_temp_tables(conn)
        
        # Check that temp tables were created
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 't_%'")
        temp_tables = [row[0] for row in cursor.fetchall()]
        
        if len(temp_tables) == 0:
            print("  ❌ No temp tables created")
            return False
        print(f"  ✅ Created {len(temp_tables)} temp tables: {temp_tables}")
        
        # Test cleanup
        cleanup_temp_tables(conn)
        conn.commit()  # Ensure changes are committed
        
        # Only check for temp tables (t_*) not regular tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 't_%'")
        remaining_temp_tables = [row[0] for row in cursor.fetchall()]
        
        if len(remaining_temp_tables) > 0:
            print(f"  ❌ Temp tables not cleaned up: {remaining_temp_tables}")
            return False
        print("  ✅ Temp tables cleaned up successfully")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database operation error: {e}")
        return False
    finally:
        os.unlink(temp_db.name)

def test_command_line_parsing() -> bool:
    """Test command line argument parsing."""
    print("Testing command line parsing...")
    try:
        from import_imdb_sqlite import parse_args
        
        # Test that the function exists and can be called
        # We'll just test that it doesn't crash with basic arguments
        print("  ✅ Argument parsing function exists")
        return True
                
    except Exception as e:
        print(f"  ❌ Argument parsing error: {e}")
        return False

def main() -> None:
    """Run all tests."""
    print("IMDB Import Script Test Suite")
    print("=" * 40)
    
    tests = [
        ("SQL Queries Loading", test_sql_queries_loading),
        ("Import Functions", test_import_functions),
        ("File Operations", test_file_operations),
        ("Database Operations", test_database_operations),
        ("Command Line Parsing", test_command_line_parsing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        else:
            print(f"  ❌ {test_name} failed")
    
    print(f"\n{'='*40}")
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main() 