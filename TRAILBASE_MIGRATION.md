# TrailBase Migration Guide

This document describes the migration from Flask/SQLAlchemy to [TrailBase](https://trailbase.io/) as the backend for the timeline application.

## What is TrailBase?

TrailBase is a blazingly fast, single-executable Firebase alternative built on Rust, SQLite, and V8 that provides:

- **Type-safe REST & realtime APIs**
- **Built-in authentication system**
- **Admin UI for data management**
- **Sub-millisecond latencies**
- **Single executable deployment**

## Migration Overview

The migration replaces the Flask/SQLAlchemy backend with TrailBase while maintaining the same functionality:

- ✅ Timeline data storage and retrieval
- ✅ People, Awards, Wars, Inventions, Space Events models
- ✅ Wikidata import functionality
- ✅ TimelineJS3 integration
- ✅ Admin interface

## New Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Flask App     │    │   TrailBase     │
│   (TimelineJS3) │◄──►│   (API Proxy)   │◄──►│   (Backend)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Setup Instructions

### 1. Prerequisites

- Python 3.12+ (already upgraded)
- Virtual environment activated

### 2. Install Dependencies

```bash
make install-dev
```

### 3. Download TrailBase

```bash
make trailbase-download
```

### 4. Initialize TrailBase

```bash
make trailbase-init
```

### 5. Start TrailBase Server

```bash
make trailbase-start
```

### 6. Import Data

```bash
make update-data
```

### 7. Run the Application

```bash
make run
```

## File Structure

### New Files

- `trailbase_config.json` - TrailBase server configuration
- `trailbase_schema.json` - Database schema definition
- `trailbase_client.py` - Python client for TrailBase API
- `thyme_trailbase.py` - Flask app using TrailBase
- `download_trailbase.py` - Script to download TrailBase binary

### Modified Files

- `import_from_json.py` - Updated to use TrailBase client
- `Makefile` - Added TrailBase-specific commands
- `requirements.txt` - Added TrailBase Python package

### Legacy Files (Still Available)

- `thyme/__init__.py` - Original Flask/SQLAlchemy app
- `init_db.py` - SQLAlchemy database initialization

## Database Schema

The TrailBase schema maintains the same data structure as the original SQLAlchemy models:

### Tables

1. **people** - Historical figures and personalities
2. **awards** - Awards and honors
3. **wars** - Wars and conflicts
4. **inventions** - Technological inventions
5. **space_events** - Space exploration events
6. **events** - Legacy events (for backward compatibility)
7. **person_awards** - Many-to-many relationship between people and awards
8. **person_wars** - Many-to-many relationship between people and wars

### Key Features

- **Foreign key relationships** maintained
- **Indexes** for performance optimization
- **Timestamps** for created_at/updated_at tracking
- **Wikidata integration** preserved

## API Endpoints

The Flask app now acts as a proxy to TrailBase, providing the same API endpoints:

### Timeline Data
- `GET /api/timeline` - Get timeline data in TimelineJS3 format

### Events (Legacy)
- `GET /api/events` - List all events
- `POST /api/events` - Create new event
- `DELETE /api/events/<id>` - Delete event

### People
- `GET /api/people` - List all people
- `POST /api/people` - Create new person

### Awards
- `GET /api/awards` - List all awards

### Wars
- `GET /api/wars` - List all wars

### Inventions
- `GET /api/inventions` - List all inventions

### Space Events
- `GET /api/space-events` - List all space events

## TrailBase Admin Interface

TrailBase provides a built-in admin interface accessible at:

```
http://localhost:8090/admin
```

Default credentials:
- Email: `admin@localhost`
- Password: `secret`

## Performance Benefits

- **11x faster** than PocketBase
- **40x faster** than Supabase
- **Sub-millisecond latencies**
- **No need for dedicated caches**
- **Consistent data without staleness**

## Migration Benefits

1. **Simplified Architecture** - Single executable backend
2. **Better Performance** - Blazingly fast APIs
3. **Built-in Admin UI** - Visual data management
4. **Type Safety** - JSON Schema validation
5. **Real-time APIs** - WebSocket support
6. **Authentication** - Built-in auth system
7. **File Storage** - Integrated file management

## Troubleshooting

### TrailBase Binary Not Found

```bash
make trailbase-download
```

### Connection Errors

Ensure TrailBase server is running:

```bash
make trailbase-start
```

### Import Errors

Check that TrailBase server is accessible at `http://localhost:8090`

### Data Migration

To migrate existing SQLAlchemy data to TrailBase:

1. Export data from SQLAlchemy database
2. Use the import scripts to load into TrailBase
3. Verify data integrity

## Development Workflow

### Adding New Features

1. Update `trailbase_schema.json` if new tables/columns needed
2. Add methods to `trailbase_client.py`
3. Update Flask routes in `thyme_trailbase.py`
4. Test with TrailBase admin interface

### Data Management

- Use TrailBase admin interface for visual data management
- Use import scripts for bulk data operations
- Use API endpoints for programmatic access

## Rollback Plan

If you need to rollback to the original Flask/SQLAlchemy setup:

1. Stop TrailBase server: `make trailbase-stop`
2. Run legacy app: `make run-legacy`
3. Use original database: `make init-db`

## Support

- [TrailBase Documentation](https://trailbase.io/)
- [TrailBase GitHub](https://github.com/trailbase/trailbase)
- [TrailBase Discord](https://discord.gg/trailbase) 