"""
SQL query loader for IMDB import script.
Provides clean separation between SQL and Python code.
"""

import os
from pathlib import Path
from typing import Optional

SQL_DIR: Path = Path(__file__).parent.parent / "sql"

def load_sql(filename: str) -> str:
    """Load SQL from a file in the sql directory."""
    sql_path: Path = SQL_DIR / filename
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")
    
    return sql_path.read_text(encoding='utf-8').strip()

class SQLQueries:
    """Container for all SQL queries used in the import process."""
    
    def __init__(self, sql_dir: Optional[str] = None) -> None:
        if sql_dir is None:
            self.sql_dir: Path = Path(__file__).parent.parent / "sql"
        else:
            self.sql_dir = Path(sql_dir)
    
    def load(self, filename: str) -> str:
        """Load SQL from a file."""
        sql_path: Path = self.sql_dir / filename
        return sql_path.read_text(encoding='utf-8').strip()
    
    @property
    def temp_tables(self) -> str:
        return self.load("temp_tables.sql")
    
    @property
    def import_titles(self) -> str:
        return self.load("import_titles.sql")
    
    @property
    def import_persons(self) -> str:
        return self.load("import_persons.sql")
    
    @property
    def import_ratings(self) -> str:
        return self.load("import_ratings.sql")
    
    @property
    def import_episodes(self) -> str:
        return self.load("import_episodes.sql")
    
    @property
    def import_principals(self) -> str:
        return self.load("import_principals.sql")
    
    @property
    def import_crew_directors(self) -> str:
        return self.load("import_crew.sql")
    
    @property
    def import_crew_writers(self) -> str:
        return self.load("import_crew_writers.sql")

# Global instance for easy access
queries: SQLQueries = SQLQueries() 