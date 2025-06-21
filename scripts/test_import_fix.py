#!/usr/bin/env python3
"""
Test script to verify the import fixes work with problematic data.
"""

import tempfile
import os
import sys

# Add the current directory to the path so we can import from the main script
sys.path.insert(0, os.path.dirname(__file__))

from import_imdb_sqlite import fix_problematic_quotes, clean_tsv_for_import

def test_problematic_data():
    """Test the fix with the specific problematic data pattern."""
    
    # Create test data with the problematic pattern
    test_data = """tconst\tordering\tnconst\tcategory\tjob\tcharacters
tt0000001\t1\tnm0000001\tactor\t\t"Rinderstall", Hann. Münden "Rinderstall", Hann. Münden
tt0000002\t1\tnm0000002\tactress\t\t"Character Name", Another "Character"
tt0000003\t1\tnm0000003\tdirector\t\t
tt0000004\t1\tnm0000004\twriter\t\t"Writer Name"
tt0000005\t1\tnm0000005\tactor\t\t"John Doe", "Jane Smith"
"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tsv', delete=False, encoding='utf-8') as f:
        f.write(test_data)
        temp_file = f.name
    
    try:
        print("Original data:")
        with open(temp_file, 'r', encoding='utf-8') as f:
            print(f.read())
        
        print("\n" + "="*50)
        print("After fixing problematic quotes:")
        
        # Test the fix_problematic_quotes function
        fixed_file = fix_problematic_quotes(temp_file)
        if os.path.exists(fixed_file):
            with open(fixed_file, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print("Fixed file was not created")
        
        print("\n" + "="*50)
        print("After full cleaning:")
        
        # Test the full cleaning function
        cleaned_file = clean_tsv_for_import(temp_file)
        if os.path.exists(cleaned_file):
            with open(cleaned_file, 'r', encoding='utf-8') as f:
                print(f.read())
        else:
            print("Cleaned file was not created")
        
        # Clean up
        if os.path.exists(fixed_file):
            os.unlink(fixed_file)
        if os.path.exists(cleaned_file):
            os.unlink(cleaned_file)
        
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)

if __name__ == "__main__":
    test_problematic_data() 