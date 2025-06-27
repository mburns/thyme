#!/usr/bin/env python3
"""
Test script for FTS5 search functionality.
This script tests the search capabilities by querying the FTS5 tables directly.
"""

import sqlite3
import sys
import os

def test_fts5_search():
    """Test the FTS5 search functionality."""
    
    # Path to the database
    db_path = "traildepot/data/main.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("Please run the TrailBase server and import data first.")
        return False
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Testing FTS5 Search Functionality")
        print("=" * 50)
        
        # Test 1: Check if FTS5 tables exist
        print("\n1. Checking FTS5 tables...")
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE '%_fts'
        """)
        fts_tables = cursor.fetchall()
        
        if not fts_tables:
            print("❌ No FTS5 tables found. Please run the migration first.")
            return False
        
        print(f"✅ Found FTS5 tables: {[table[0] for table in fts_tables]}")
        
        # Test 2: Check if data exists in FTS5 tables
        print("\n2. Checking data in FTS5 tables...")
        for table in fts_tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   {table_name}: {count} rows")
        
        # Test 3: Test basic search functionality
        print("\n3. Testing basic search...")
        test_queries = [
            "godfather",
            "tom hanks",
            "action",
            "1999",
            "drama"
        ]
        
        for query in test_queries:
            print(f"\n   Searching for: '{query}'")
            
            # Search in titles_fts
            cursor.execute("""
                SELECT primaryTitle, titleType, startYear, genres, rank
                FROM titles_fts 
                WHERE titles_fts MATCH ? 
                ORDER BY rank 
                LIMIT 3
            """, (query,))
            
            title_results = cursor.fetchall()
            if title_results:
                print(f"     Titles found: {len(title_results)}")
                for result in title_results:
                    print(f"       - {result[0]} ({result[1]}, {result[2]}) - {result[3]} (rank: {result[4]})")
            else:
                print("     No titles found")
            
            # Search in persons_fts
            cursor.execute("""
                SELECT primaryName, birthYear, deathYear, primaryProfession, rank
                FROM persons_fts 
                WHERE persons_fts MATCH ? 
                ORDER BY rank 
                LIMIT 3
            """, (query,))
            
            person_results = cursor.fetchall()
            if person_results:
                print(f"     People found: {len(person_results)}")
                for result in person_results:
                    years = f"{result[1]}-{result[2]}" if result[2] else f"{result[1]}-present"
                    print(f"       - {result[0]} ({years}) - {result[3]} (rank: {result[4]})")
            else:
                print("     No people found")
        
        # Test 4: Test combined search
        print("\n4. Testing combined search...")
        cursor.execute("""
            SELECT type, primaryTitle, startYear, genres, rank
            FROM search_fts 
            WHERE search_fts MATCH 'godfather' 
            ORDER BY rank 
            LIMIT 5
        """)
        
        combined_results = cursor.fetchall()
        if combined_results:
            print(f"   Combined search results: {len(combined_results)}")
            for result in combined_results:
                print(f"     - [{result[0]}] {result[1]} ({result[2]}) - {result[3]} (rank: {result[4]})")
        else:
            print("   No combined search results")
        
        # Test 5: Test search with filters
        print("\n5. Testing search with year filter...")
        cursor.execute("""
            SELECT primaryTitle, startYear, genres, rank
            FROM titles_fts 
            WHERE titles_fts MATCH 'action' AND startYear = 1999
            ORDER BY rank 
            LIMIT 3
        """)
        
        filtered_results = cursor.fetchall()
        if filtered_results:
            print(f"   Action movies from 1999: {len(filtered_results)}")
            for result in filtered_results:
                print(f"     - {result[0]} ({result[1]}) - {result[2]} (rank: {result[3]})")
        else:
            print("   No action movies from 1999 found")
        
        print("\n✅ FTS5 search functionality test completed successfully!")
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    """Main function."""
    print("Thyme IMDB - FTS5 Search Test")
    print("=" * 40)
    
    success = test_fts5_search()
    
    if success:
        print("\n🎉 All tests passed! FTS5 search is working correctly.")
        print("\nNext steps:")
        print("1. Start the TrailBase server")
        print("2. Build the static site: make build")
        print("3. Visit the search page at /search.html")
    else:
        print("\n❌ Tests failed. Please check the database and migrations.")
        sys.exit(1)

if __name__ == "__main__":
    main() 