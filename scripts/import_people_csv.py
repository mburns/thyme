#!/usr/bin/env python3
"""
Import people data from CSV file into TrailBase.
"""
import argparse
import csv
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from trailbase_client import TimelineTrailBaseSync


def parse_year(year_str: str) -> Optional[int]:
    """Parse year string to integer, handling various formats."""
    if not year_str or year_str.strip() == '':
        return None
    
    try:
        # Remove any non-digit characters and get the year
        year_str = year_str.strip()
        # Handle BCE/BC years (negative years)
        if any(bc in year_str.upper() for bc in ['BCE', 'BC', 'B.C.E.', 'B.C.']):
            # Extract the number and make it negative
            year_num = int(''.join(filter(str.isdigit, year_str)))
            return -year_num
        
        # Handle CE/AD years (positive years)
        if any(ad in year_str.upper() for ad in ['CE', 'AD', 'C.E.', 'A.D.']):
            year_num = int(''.join(filter(str.isdigit, year_str)))
            return year_num
        
        # Handle plain year numbers
        year_num = int(year_str)
        # Assume years before 1000 are CE, years after 1000 are as-is
        if year_num < 1000:
            return year_num
        return year_num
        
    except (ValueError, TypeError):
        return None


def calculate_age_at_death(birth_year: Optional[int], death_year: Optional[int]) -> Optional[int]:
    """Calculate age at death from birth and death years."""
    if birth_year is None or death_year is None:
        return None
    
    # Handle BCE years (negative)
    if birth_year < 0 and death_year < 0:
        return abs(birth_year) - abs(death_year)
    elif birth_year < 0 and death_year > 0:
        return abs(birth_year) + death_year
    else:
        return death_year - birth_year


def validate_age_at_death(calculated_age: Optional[int], csv_age: Optional[int]) -> Optional[int]:
    """Validate and return the most likely age at death."""
    if csv_age is None:
        return calculated_age
    if calculated_age is None:
        return csv_age
    
    # If both are available, prefer the CSV age but warn if they differ significantly
    if abs(calculated_age - csv_age) > 5:
        print(f"Warning: Age discrepancy - calculated: {calculated_age}, CSV: {csv_age}")
    
    return csv_age


def parse_csv_row(row: Dict[str, str]) -> Optional[Dict]:
    """Parse a CSV row into a person data dictionary."""
    try:
        # Extract basic information
        name = row.get('Name', '').strip()
        if not name:
            print(f"Warning: Skipping row with empty name (ID: {row.get('Id', 'unknown')})")
            return None
        
        # Parse years
        birth_year = parse_year(row.get('Birth year', ''))
        death_year = parse_year(row.get('Death year', ''))
        
        # Calculate age at death
        calculated_age = calculate_age_at_death(birth_year, death_year)
        csv_age = parse_year(row.get('Age of death', ''))  # Assuming this is a number
        age_at_death = validate_age_at_death(calculated_age, csv_age)
        
        # Create person data
        person_data = {
            'name': name,
            'description': row.get('Short description', '').strip(),
            'occupation': row.get('Occupation', '').strip(),
            'nationality': row.get('Country', '').strip(),
        }
        
        # Add dates if available
        if birth_year:
            # Convert year to datetime (January 1st of that year)
            if birth_year < 0:
                # Handle BCE years - use a reasonable date format
                person_data['birth_date'] = f"{abs(birth_year)}-01-01T00:00:00Z"
                person_data['birth_year_bce'] = True
            else:
                person_data['birth_date'] = f"{birth_year}-01-01T00:00:00Z"
        
        if death_year:
            if death_year < 0:
                person_data['death_date'] = f"{abs(death_year)}-01-01T00:00:00Z"
                person_data['death_year_bce'] = True
            else:
                person_data['death_date'] = f"{death_year}-01-01T00:00:00Z"
        
        # Add additional metadata
        if row.get('Gender', '').strip():
            person_data['gender'] = row.get('Gender', '').strip()
        
        if row.get('Manner of death', '').strip():
            person_data['manner_of_death'] = row.get('Manner of death', '').strip()
        
        if age_at_death is not None:
            person_data['age_at_death'] = age_at_death
        
        # Add original ID for reference
        if row.get('Id', '').strip():
            person_data['original_id'] = row.get('Id', '').strip()
        
        return person_data
        
    except Exception as e:
        print(f"Error parsing row: {e}")
        print(f"Row data: {row}")
        return None


def import_csv_to_trailbase(csv_file: str, trailbase_client: TimelineTrailBaseSync, 
                           dry_run: bool = False) -> Dict[str, int]:
    """Import CSV data into TrailBase."""
    stats = {
        'total_rows': 0,
        'successful_imports': 0,
        'skipped_rows': 0,
        'errors': 0
    }
    
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found.")
        return stats
    
    print(f"Importing data from '{csv_file}'...")
    if dry_run:
        print("DRY RUN MODE - No data will be imported")
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            # Try to detect the dialect
            sample = file.read(1024)
            file.seek(0)
            
            try:
                dialect = csv.Sniffer().sniff(sample)
                reader = csv.DictReader(file, dialect=dialect)
            except csv.Error:
                # Fall back to default dialect
                reader = csv.DictReader(file)
            
            # Validate headers
            expected_headers = {
                'Id', 'Name', 'Short description', 'Gender', 'Country', 
                'Occupation', 'Birth year', 'Death year', 'Manner of death', 'Age of death'
            }
            
            actual_headers = set(reader.fieldnames or [])
            missing_headers = expected_headers - actual_headers
            extra_headers = actual_headers - expected_headers
            
            if missing_headers:
                print(f"Warning: Missing expected headers: {missing_headers}")
            if extra_headers:
                print(f"Info: Extra headers found: {extra_headers}")
            
            print(f"Found headers: {list(reader.fieldnames)}")
            
            # Process rows
            for row_num, row in enumerate(reader, start=2):  # Start at 2 because row 1 is headers
                stats['total_rows'] += 1
                
                try:
                    person_data = parse_csv_row(row)
                    
                    if person_data is None:
                        stats['skipped_rows'] += 1
                        continue
                    
                    if dry_run:
                        print(f"Would import: {person_data['name']} ({person_data.get('birth_date', 'unknown birth')} - {person_data.get('death_date', 'unknown death')})")
                        stats['successful_imports'] += 1
                    else:
                        # Check if person already exists (by name and birth year)
                        existing_people = trailbase_client.get_people({
                            'name': person_data['name']
                        })
                        
                        if existing_people:
                            print(f"Skipping existing person: {person_data['name']}")
                            stats['skipped_rows'] += 1
                            continue
                        
                        # Import the person
                        imported_person = trailbase_client.create_person(person_data)
                        print(f"Imported: {person_data['name']} (ID: {imported_person.get('id', 'unknown')})")
                        stats['successful_imports'] += 1
                
                except Exception as e:
                    print(f"Error processing row {row_num}: {e}")
                    stats['errors'] += 1
                    continue
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        stats['errors'] += 1
    
    return stats


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Import people data from CSV into TrailBase")
    parser.add_argument("csv_file", help="Path to the CSV file")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be imported without actually importing")
    parser.add_argument("--trailbase-url", default="http://localhost:8090",
                       help="TrailBase server URL (default: http://localhost:8090)")
    parser.add_argument("--auth-token", 
                       help="TrailBase authentication token")
    
    args = parser.parse_args()
    
    # Initialize TrailBase client
    try:
        trailbase_client = TimelineTrailBaseSync(base_url=args.trailbase_url, auth_token=args.auth_token)
        print(f"Connected to TrailBase at {args.trailbase_url}")
    except Exception as e:
        print(f"Error connecting to TrailBase: {e}")
        print("Make sure TrailBase server is running: make trailbase-start")
        print("You may need to provide an auth token with --auth-token")
        sys.exit(1)
    
    # Import the data
    stats = import_csv_to_trailbase(args.csv_file, trailbase_client, args.dry_run)
    
    # Print summary
    print("\n" + "="*50)
    print("IMPORT SUMMARY")
    print("="*50)
    print(f"Total rows processed: {stats['total_rows']}")
    print(f"Successfully imported: {stats['successful_imports']}")
    print(f"Skipped (existing/empty): {stats['skipped_rows']}")
    print(f"Errors: {stats['errors']}")
    
    if args.dry_run:
        print("\nThis was a dry run. No data was actually imported.")
        print("Run without --dry-run to import the data.")
    else:
        print(f"\nImport completed successfully!")
        print("You can now view the data in TrailBase admin interface:")
        print(f"  {args.trailbase_url}/admin")


if __name__ == "__main__":
    main() 