# IMDB Data Import Guide

This guide explains how to import IMDB (Internet Movie Database) data into TrailBase for analysis and querying.

## 📋 Overview

The IMDB import system consists of:

1. **Database Schema** - Strict SQL tables for IMDB data
2. **Import Script** - Python script to process TSV files
3. **Migration Files** - SQL migrations for schema creation and optimization
4. **Shell Script** - Automated import process

## 🗄️ Database Schema

### Core Tables

#### `persons`
- **Purpose**: Stores actors, directors, writers, and other crew members
- **Key Fields**: `nconst` (IMDB ID), `primary_name`, `birth_year`, `death_year`, `primary_profession`
- **Constraints**: Strict table with UUID primary keys, birth/death year validation

#### `titles`
- **Purpose**: Stores movies, TV shows, episodes, and other media
- **Key Fields**: `tconst` (IMDB ID), `title_type`, `primary_title`, `start_year`, `genres`
- **Constraints**: Strict table with type validation, episode-specific fields for TV shows

#### `ratings`
- **Purpose**: Stores user ratings and vote counts
- **Key Fields**: `title_id`, `average_rating`, `num_votes`
- **Constraints**: Rating range validation (0.0-10.0), unique per title

#### `title_akas`
- **Purpose**: Alternative titles and translations
- **Key Fields**: `title_id`, `title`, `region`, `language`, `types`
- **Constraints**: JSON arrays for types and attributes

#### `title_crew`
- **Purpose**: Directors and writers for titles
- **Key Fields**: `title_id`, `directors`, `writers`
- **Constraints**: JSON arrays of person IDs

#### `title_principals`
- **Purpose**: Detailed cast and crew roles
- **Key Fields**: `title_id`, `person_id`, `category`, `job`, `characters`
- **Constraints**: Category validation, JSON arrays for characters

### Views and Optimizations

- **`top_rated_movies`** - High-rated movies with sufficient votes
- **`top_rated_tv_series`** - High-rated TV series
- **`most_prolific_actors`** - Actors with most roles
- **`movie_details`** - Comprehensive movie information

## 📁 Required Data Files

Download the IMDB dataset from [IMDB Datasets](https://www.imdb.com/interfaces/) and place the following compressed TSV files in the `data/` directory:

```
data/
├── name.basics.tsv.gz          # Person information
├── title.basics.tsv.gz         # Title information
├── title.episode.tsv.gz        # Episode relationships
├── title.ratings.tsv.gz        # Ratings and votes
├── title.akas.tsv.gz           # Alternative titles
├── title.crew.tsv.gz           # Directors and writers
└── title.principals.tsv.gz     # Cast and crew details
```

### File Formats

All files are gzipped TSV (Tab-Separated Values) with the following headers:

#### `name.basics.tsv.gz`
```
nconst	primaryName	birthYear	deathYear	primaryProfession	knownForTitles
```

#### `title.basics.tsv.gz`
```
tconst	titleType	primaryTitle	originalTitle	isAdult	startYear	endYear	runtimeMinutes	genres
```

#### `title.episode.tsv.gz`
```
tconst	parentTconst	seasonNumber	episodeNumber
```

#### `title.ratings.tsv.gz`
```
tconst	averageRating	numVotes
```

#### `title.akas.tsv.gz`
```
titleId	ordering	title	region	language	types	attributes	isOriginalTitle
```

#### `title.crew.tsv.gz`
```
tconst	directors	writers
```

#### `title.principals.tsv.gz`
```
tconst	ordering	nconst	category	job	characters
```

## 🚀 Quick Start

### 1. Prerequisites

- TrailBase running on port 4000
- Python 3.6+
- IMDB dataset files in `data/` directory

### 2. Run the Import

```bash
# Check prerequisites only
./scripts/import_imdb.sh --check-only

# Run the full import
./scripts/import_imdb.sh

# Custom data directory and batch size
./scripts/import_imdb.sh --data-dir /path/to/imdb/data --batch-size 500
```

### 3. Manual Import

```bash
# Run the Python script directly
python3 scripts/import_imdb.py --data-dir data/ --batch-size 1000
```

## 🔧 Configuration

### Environment Variables

- `VITE_API_URL` - TrailBase API URL (default: `http://localhost:4000`)

### Script Options

- `--data-dir` - Directory containing IMDB TSV files (default: `data/`)
- `--db-path` - Path to TrailBase database (default: `traildepot/data/main.db`)
- `--batch-size` - Number of records per batch (default: 1000)

## 📊 Performance Considerations

### Batch Processing
- Default batch size: 1000 records
- Adjust based on available memory
- Larger batches = faster import but more memory usage

### Indexes
The schema includes optimized indexes for:
- Primary key lookups (`nconst`, `tconst`)
- Common queries (title type, year, ratings)
- Foreign key relationships
- JSON field queries

### Memory Usage
- Person cache: ~50MB for 10M persons
- Title cache: ~100MB for 10M titles
- Total memory: ~200-500MB depending on dataset size

## 🔍 Query Examples

### Top Rated Movies
```sql
SELECT * FROM top_rated_movies LIMIT 10;
```

### Actor Filmography
```sql
SELECT 
    t.primary_title,
    t.start_year,
    tp.category,
    tp.characters
FROM persons p
JOIN title_principals tp ON p.id = tp.person_id
JOIN titles t ON tp.title_id = t.id
WHERE p.nconst = 'nm0000375'  -- Robert De Niro
ORDER BY t.start_year DESC;
```

### Movies by Genre
```sql
SELECT 
    t.primary_title,
    t.start_year,
    r.average_rating
FROM titles t
JOIN ratings r ON t.id = r.title_id
WHERE t.title_type = 'movie'
    AND json_extract(t.genres, '$[0]') = 'Action'
    AND r.num_votes >= 1000
ORDER BY r.average_rating DESC;
```

### TV Series with Most Episodes
```sql
SELECT 
    t.primary_title,
    t.start_year,
    COUNT(e.id) as episode_count
FROM titles t
LEFT JOIN titles e ON e.parent_tconst = t.tconst
WHERE t.title_type = 'tvSeries'
GROUP BY t.id, t.primary_title, t.start_year
ORDER BY episode_count DESC
LIMIT 10;
```

## 🛠️ Troubleshooting

### Common Issues

#### TrailBase Not Running
```
[ERROR] TrailBase is not running on port 4000
```
**Solution**: Start TrailBase with `./trailbase run`

#### Missing Data Files
```
[ERROR] Missing required files: name.basics.tsv.gz
```
**Solution**: Download IMDB dataset and place files in `data/` directory

#### Database Locked
```
[ERROR] database is locked
```
**Solution**: Ensure no other processes are accessing the database

#### Memory Issues
```
[ERROR] MemoryError
```
**Solution**: Reduce batch size with `--batch-size 500`

### Log Files

- **`imdb_import.log`** - Detailed import logs
- **`traildepot/data/logs.db`** - TrailBase system logs

### Performance Monitoring

Monitor import progress:
```bash
# Watch log file
tail -f imdb_import.log

# Check database size
ls -lh traildepot/data/main.db

# Monitor memory usage
top -p $(pgrep -f import_imdb.py)
```

## 📈 Statistics

After import, check statistics:
```sql
SELECT * FROM imdb_stats;
```

Expected record counts (approximate):
- **Persons**: 10-15 million
- **Titles**: 8-12 million
- **Ratings**: 1-2 million
- **Principals**: 50-100 million
- **AKAs**: 20-30 million

## 🔄 Updating Data

To update with new IMDB data:

1. Download latest dataset
2. Backup existing database
3. Run import script with new data
4. Update statistics: `SELECT update_all_stats();`

## 📚 Additional Resources

- [IMDB Datasets Documentation](https://www.imdb.com/interfaces/)
- [TrailBase Documentation](https://trailbase.io/docs)
- [SQLite JSON Functions](https://www.sqlite.org/json1.html)

## 🤝 Contributing

To improve the import process:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with sample data
5. Submit a pull request

## 📄 License

This import system is part of the Thyme project and follows the same MIT license. 