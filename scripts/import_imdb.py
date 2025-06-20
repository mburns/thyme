#!/usr/bin/env python3
"""
IMDB Data Import Script for TrailBase

This script processes compressed TSV files from IMDB and imports them into TrailBase.
It handles the relationships between persons, titles, ratings, and other metadata.

Usage:
    python scripts/import_imdb.py [--data-dir data/] [--batch-size 1000]
"""

import os
import sys
import json
import gzip
import sqlite3
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('imdb_import.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class IMDBImporter:
    def __init__(self, db_path: str, batch_size: int = 1000):
        self.db_path = db_path
        self.batch_size = batch_size
        self.conn = None
        self.cursor = None
        
        # Caches for lookups
        self.person_cache = {}  # nconst -> id
        self.title_cache = {}   # tconst -> id
        
    def connect(self):
        """Connect to the TrailBase database"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.cursor = self.conn.cursor()
            logger.info(f"Connected to database: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def parse_tsv_line(self, line: str) -> List[str]:
        """Parse a TSV line, handling quoted fields"""
        if '\t' not in line:
            return [line.strip()]
        
        fields = []
        current_field = ""
        in_quotes = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == '\t' and not in_quotes:
                fields.append(current_field)
                current_field = ""
            else:
                current_field += char
        
        fields.append(current_field)
        return [field.strip() for field in fields]
    
    def safe_int(self, value: str) -> Optional[int]:
        """Safely convert string to integer"""
        if value == '\\N' or not value:
            return None
        try:
            return int(value)
        except ValueError:
            return None
    
    def safe_float(self, value: str) -> Optional[float]:
        """Safely convert string to float"""
        if value == '\\N' or not value:
            return None
        try:
            return float(value)
        except ValueError:
            return None
    
    def parse_json_array(self, value: str) -> Optional[str]:
        """Parse comma-separated values as JSON array"""
        if value == '\\N' or not value:
            return None
        items = [item.strip() for item in value.split(',') if item.strip()]
        return json.dumps(items) if items else None
    
    def import_persons(self, file_path: str):
        """Import persons from name.basics.tsv"""
        logger.info(f"Importing persons from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 6:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    nconst, primary_name, birth_year, death_year, primary_profession, known_for_titles = fields
                    
                    # Parse data
                    birth_year_int = self.safe_int(birth_year)
                    death_year_int = self.safe_int(death_year)
                    known_for_json = self.parse_json_array(known_for_titles)
                    
                    batch.append((
                        nconst,
                        primary_name,
                        birth_year_int,
                        death_year_int,
                        primary_profession if primary_profession != '\\N' else None,
                        known_for_json
                    ))
                    
                    if len(batch) >= self.batch_size:
                        self._insert_persons_batch(batch)
                        count += len(batch)
                        batch = []
                        logger.info(f"Imported {count} persons so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # Insert remaining batch
        if batch:
            self._insert_persons_batch(batch)
            count += len(batch)
        
        logger.info(f"Completed importing {count} persons")
    
    def _insert_persons_batch(self, batch: List[tuple]):
        """Insert a batch of persons"""
        try:
            self.cursor.executemany("""
                INSERT INTO persons (nconst, primary_name, birth_year, death_year, primary_profession, known_for_titles)
                VALUES (?, ?, ?, ?, ?, ?)
            """, batch)
            self.conn.commit()
            
            # Update cache
            for nconst, _, _, _, _, _ in batch:
                self.cursor.execute("SELECT id FROM persons WHERE nconst = ?", (nconst,))
                result = self.cursor.fetchone()
                if result:
                    self.person_cache[nconst] = result[0]
        
        except Exception as e:
            logger.error(f"Error inserting persons batch: {e}")
            self.conn.rollback()
            raise
    
    def import_titles(self, file_path: str):
        """Import titles from title.basics.tsv"""
        logger.info(f"Importing titles from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 9:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    (tconst, title_type, primary_title, original_title, is_adult, 
                     start_year, end_year, runtime_minutes, genres) = fields
                    
                    # Parse data
                    start_year_int = self.safe_int(start_year)
                    end_year_int = self.safe_int(end_year)
                    runtime_int = self.safe_int(runtime_minutes)
                    is_adult_bool = is_adult == '1'
                    genres_json = self.parse_json_array(genres)
                    
                    batch.append((
                        tconst,
                        title_type,
                        primary_title,
                        original_title if original_title != '\\N' else None,
                        is_adult_bool,
                        start_year_int,
                        end_year_int,
                        runtime_int,
                        genres_json,
                        None,  # parent_tconst
                        None,  # season_number
                        None   # episode_number
                    ))
                    
                    if len(batch) >= self.batch_size:
                        self._insert_titles_batch(batch)
                        count += len(batch)
                        batch = []
                        logger.info(f"Imported {count} titles so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # Insert remaining batch
        if batch:
            self._insert_titles_batch(batch)
            count += len(batch)
        
        logger.info(f"Completed importing {count} titles")
    
    def _insert_titles_batch(self, batch: List[tuple]):
        """Insert a batch of titles"""
        try:
            self.cursor.executemany("""
                INSERT INTO titles (tconst, title_type, primary_title, original_title, is_adult, 
                                   start_year, end_year, runtime_minutes, genres, parent_tconst, 
                                   season_number, episode_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            self.conn.commit()
            
            # Update cache
            for tconst, _, _, _, _, _, _, _, _, _, _, _ in batch:
                self.cursor.execute("SELECT id FROM titles WHERE tconst = ?", (tconst,))
                result = self.cursor.fetchone()
                if result:
                    self.title_cache[tconst] = result[0]
        
        except Exception as e:
            logger.error(f"Error inserting titles batch: {e}")
            self.conn.rollback()
            raise
    
    def import_episodes(self, file_path: str):
        """Import episodes and update parent titles"""
        logger.info(f"Importing episodes from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 4:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    tconst, parent_tconst, season_number, episode_number = fields
                    
                    # Parse data
                    season_int = self.safe_int(season_number)
                    episode_int = self.safe_int(episode_number)
                    
                    # Update the title record with episode information
                    self.cursor.execute("""
                        UPDATE titles 
                        SET parent_tconst = ?, season_number = ?, episode_number = ?
                        WHERE tconst = ?
                    """, (parent_tconst, season_int, episode_int, tconst))
                    
                    count += 1
                    if count % self.batch_size == 0:
                        self.conn.commit()
                        logger.info(f"Updated {count} episodes so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        self.conn.commit()
        logger.info(f"Completed updating {count} episodes")
    
    def import_ratings(self, file_path: str):
        """Import ratings"""
        logger.info(f"Importing ratings from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 3:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    tconst, average_rating, num_votes = fields
                    
                    # Get title ID
                    title_id = self.title_cache.get(tconst)
                    if not title_id:
                        logger.warning(f"Line {line_num}: Title not found: {tconst}")
                        continue
                    
                    # Parse data
                    rating_float = self.safe_float(average_rating)
                    votes_int = self.safe_int(num_votes)
                    
                    if rating_float is None or votes_int is None:
                        continue
                    
                    batch.append((title_id, rating_float, votes_int))
                    
                    if len(batch) >= self.batch_size:
                        self._insert_ratings_batch(batch)
                        count += len(batch)
                        batch = []
                        logger.info(f"Imported {count} ratings so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # Insert remaining batch
        if batch:
            self._insert_ratings_batch(batch)
            count += len(batch)
        
        logger.info(f"Completed importing {count} ratings")
    
    def _insert_ratings_batch(self, batch: List[tuple]):
        """Insert a batch of ratings"""
        try:
            self.cursor.executemany("""
                INSERT INTO ratings (title_id, average_rating, num_votes)
                VALUES (?, ?, ?)
            """, batch)
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error inserting ratings batch: {e}")
            self.conn.rollback()
            raise
    
    def import_akas(self, file_path: str):
        """Import alternative titles (AKAs)"""
        logger.info(f"Importing AKAs from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 8:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    (title_id, ordering, title, region, language, types, 
                     attributes, is_original_title) = fields
                    
                    # Get title ID
                    title_uuid = self.title_cache.get(title_id)
                    if not title_uuid:
                        logger.warning(f"Line {line_num}: Title not found: {title_id}")
                        continue
                    
                    # Parse data
                    ordering_int = self.safe_int(ordering)
                    types_json = self.parse_json_array(types)
                    attributes_json = self.parse_json_array(attributes)
                    is_original_bool = is_original_title == '1'
                    
                    if ordering_int is None:
                        continue
                    
                    batch.append((
                        title_uuid,
                        ordering_int,
                        title,
                        region if region != '\\N' else None,
                        language if language != '\\N' else None,
                        types_json,
                        attributes_json,
                        is_original_bool
                    ))
                    
                    if len(batch) >= self.batch_size:
                        self._insert_akas_batch(batch)
                        count += len(batch)
                        batch = []
                        logger.info(f"Imported {count} AKAs so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # Insert remaining batch
        if batch:
            self._insert_akas_batch(batch)
            count += len(batch)
        
        logger.info(f"Completed importing {count} AKAs")
    
    def _insert_akas_batch(self, batch: List[tuple]):
        """Insert a batch of AKAs"""
        try:
            self.cursor.executemany("""
                INSERT INTO title_akas (title_id, ordering, title, region, language, types, attributes, is_original_title)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error inserting AKAs batch: {e}")
            self.conn.rollback()
            raise
    
    def import_crew(self, file_path: str):
        """Import crew information"""
        logger.info(f"Importing crew from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 3:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    tconst, directors, writers = fields
                    
                    # Get title ID
                    title_uuid = self.title_cache.get(tconst)
                    if not title_uuid:
                        logger.warning(f"Line {line_num}: Title not found: {tconst}")
                        continue
                    
                    # Parse data
                    directors_json = self.parse_json_array(directors)
                    writers_json = self.parse_json_array(writers)
                    
                    batch.append((title_uuid, directors_json, writers_json))
                    
                    if len(batch) >= self.batch_size:
                        self._insert_crew_batch(batch)
                        count += len(batch)
                        batch = []
                        logger.info(f"Imported {count} crew records so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # Insert remaining batch
        if batch:
            self._insert_crew_batch(batch)
            count += len(batch)
        
        logger.info(f"Completed importing {count} crew records")
    
    def _insert_crew_batch(self, batch: List[tuple]):
        """Insert a batch of crew records"""
        try:
            self.cursor.executemany("""
                INSERT INTO title_crew (title_id, directors, writers)
                VALUES (?, ?, ?)
            """, batch)
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error inserting crew batch: {e}")
            self.conn.rollback()
            raise
    
    def import_principals(self, file_path: str):
        """Import principal cast and crew"""
        logger.info(f"Importing principals from {file_path}")
        
        batch = []
        count = 0
        
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, 2):
                try:
                    fields = self.parse_tsv_line(line.strip())
                    if len(fields) < 6:
                        logger.warning(f"Line {line_num}: Invalid number of fields: {len(fields)}")
                        continue
                    
                    tconst, ordering, nconst, category, job, characters = fields
                    
                    # Get title and person IDs
                    title_uuid = self.title_cache.get(tconst)
                    person_uuid = self.person_cache.get(nconst)
                    
                    if not title_uuid:
                        logger.warning(f"Line {line_num}: Title not found: {tconst}")
                        continue
                    
                    if not person_uuid:
                        logger.warning(f"Line {line_num}: Person not found: {nconst}")
                        continue
                    
                    # Parse data
                    ordering_int = self.safe_int(ordering)
                    characters_json = self.parse_json_array(characters)
                    
                    if ordering_int is None:
                        continue
                    
                    batch.append((
                        title_uuid,
                        person_uuid,
                        ordering_int,
                        category,
                        job if job != '\\N' else None,
                        characters_json
                    ))
                    
                    if len(batch) >= self.batch_size:
                        self._insert_principals_batch(batch)
                        count += len(batch)
                        batch = []
                        logger.info(f"Imported {count} principal records so far...")
                
                except Exception as e:
                    logger.error(f"Error processing line {line_num}: {e}")
                    continue
        
        # Insert remaining batch
        if batch:
            self._insert_principals_batch(batch)
            count += len(batch)
        
        logger.info(f"Completed importing {count} principal records")
    
    def _insert_principals_batch(self, batch: List[tuple]):
        """Insert a batch of principal records"""
        try:
            self.cursor.executemany("""
                INSERT INTO title_principals (title_id, person_id, ordering, category, job, characters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, batch)
            self.conn.commit()
        
        except Exception as e:
            logger.error(f"Error inserting principals batch: {e}")
            self.conn.rollback()
            raise
    
    def run_import(self, data_dir: str):
        """Run the complete import process"""
        data_path = Path(data_dir)
        
        # Check if data directory exists
        if not data_path.exists():
            logger.error(f"Data directory not found: {data_dir}")
            return
        
        try:
            self.connect()
            
            # Import in order to maintain referential integrity
            files_to_import = [
                ('name.basics.tsv.gz', self.import_persons),
                ('title.basics.tsv.gz', self.import_titles),
                ('title.episode.tsv.gz', self.import_episodes),
                ('title.ratings.tsv.gz', self.import_ratings),
                ('title.akas.tsv.gz', self.import_akas),
                ('title.crew.tsv.gz', self.import_crew),
                ('title.principals.tsv.gz', self.import_principals),
            ]
            
            for filename, import_func in files_to_import:
                file_path = data_path / filename
                if file_path.exists():
                    logger.info(f"Processing {filename}...")
                    import_func(str(file_path))
                else:
                    logger.warning(f"File not found: {filename}")
            
            logger.info("Import completed successfully!")
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            raise
        finally:
            self.disconnect()

def main():
    parser = argparse.ArgumentParser(description='Import IMDB data into TrailBase')
    parser.add_argument('--data-dir', default='data/', help='Directory containing IMDB TSV files')
    parser.add_argument('--db-path', default='traildepot/data/main.db', help='Path to TrailBase database')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size for database inserts')
    
    args = parser.parse_args()
    
    importer = IMDBImporter(args.db_path, args.batch_size)
    importer.run_import(args.data_dir)

if __name__ == '__main__':
    main() 