# Thyme 🌿

A minimalist IMDB data browser built with TrailBase, featuring efficient data import and a clean, modern interface.

[![CI](https://github.com/yourusername/thyme/workflows/CI/badge.svg)](https://github.com/yourusername/thyme/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Shell Script](https://img.shields.io/badge/shell-bash-blue.svg)](https://www.gnu.org/software/bash/)
[![Code style: shellcheck](https://img.shields.io/badge/code%20style-shellcheck-000000.svg)](https://github.com/koalaman/shellcheck)

## ✨ Features

- **Efficient Data Import**: Uses SQLite's bulk import capabilities for fast IMDB data loading
- **Modern UI**: Clean, responsive interface built with Alpine.js
- **Comprehensive Search**: Full-text search across movies, TV shows, people, and genres using FTS5
- **Real-time Data**: Dynamic content loading with pagination
- **Static Site Generation**: Build process creates optimized static files
- **Professional Development**: Full CI/CD pipeline with shell script quality checks

## 🔍 Search Functionality

The website includes powerful full-text search capabilities powered by SQLite's FTS5:

### Search Features
- **Multi-field Search**: Search across titles, people, genres, and years
- **Filtered Results**: Filter by content type (titles, persons, genres, years)
- **Pagination**: Navigate through large result sets
- **Real-time Search**: Debounced search as you type
- **Ranked Results**: Results are ranked by relevance using FTS5 ranking

### Search Examples
- Movie titles: "The Godfather", "Star Wars"
- Actor names: "Tom Hanks", "Meryl Streep"
- Genres: "action", "drama", "comedy"
- Years: "1999", "2020s", "1980s"
- Combined searches: "action 2023", "Tom Hanks drama"

### Technical Implementation
- **FTS5 Virtual Tables**: Separate search indexes for titles and persons
- **Combined Search View**: Unified search across all content types
- **TrailBase API**: RESTful search endpoint at `/search`
- **Alpine.js Frontend**: Reactive search interface with debouncing
- **Automatic Sync**: Database triggers keep search indexes up-to-date

### Testing Search
```bash
# Test the search functionality
make test-search

# Start TrailBase server and test the API
trailbase serve
curl "http://localhost:8080/search?q=godfather&titles=true&persons=true"
```

## 🚀 Quick Start

### Prerequisites

- Bash 4.0 or higher
- SQLite 3.39 or higher
- Git
- Make (optional, for using Makefile commands)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/thyme.git
   cd thyme
   ```

2. **Check system dependencies**
   ```bash
   make check-deps
   ```

3. **Set up development environment**
   ```bash
   # Install development dependencies (pre-commit)
   make install-dev
   
   # Install pre-commit hooks
   make setup-hooks
   ```

4. **Start TrailBase server** (to create the database)
   ```bash
   # Start TrailBase (you'll need to install it separately)
   trailbase serve
   ```

5. **Import IMDB data**
   ```bash
   make import-data
   ```

6. **Build the static site**
   ```bash
   make build
   ```

7. **Serve the site**
   ```bash
   # Using Python's built-in server
   python -m http.server --directory dist
   
   # Or using any static file server
   cd dist && python -m http.server 8000
   ```

Visit `http://localhost:8000` to see your IMDB browser!

## 🛠️ Development

### Available Commands

```bash
make help          # Show all available commands
make check-deps    # Check system dependencies
make install-dev   # Install development dependencies
make setup-hooks   # Install pre-commit hooks
make lint          # Run linting checks (shellcheck)
make test          # Run tests and validation
make build         # Build static site
make clean         # Clean build artifacts
make all           # Run all checks
make info          # Show project information
```

### Code Quality

This project uses several tools to maintain high code quality:

- **Pre-commit hooks** - Automated checks before each commit
- **shellcheck** - Shell script linting and best practices
- **shfmt** - Shell script formatting
- **GitHub Actions** - Continuous integration
- **Markdown linting** - Documentation quality

### Project Structure

```
thyme/
├── templates/              # HTML templates
├── static/                # Static assets (CSS, JS, images)
├── traildepot/            # TrailBase configuration and migrations
│   └── migrations/        # Database migrations
├── data/                  # IMDB data files (downloaded automatically)
├── dist/                  # Built static site (generated)
├── *.sh                   # Shell scripts
├── .github/workflows/     # CI/CD configuration
└── docs/                  # Documentation
```

## 📊 Data Import

The project includes efficient data import scripts that:

1. **Download datasets** from [IMDB's official source](https://datasets.imdbws.com/)
2. **Use SQLite's bulk import** for maximum performance
3. **Handle data transformation** and foreign key relationships
4. **Provide progress tracking** and error handling

### Import Process

```bash
# The import script will:
# 1. Download missing datasets automatically
# 2. Decompress .tsv.gz files
# 3. Use SQLite's .import command for bulk loading
# 4. Transform data with proper types and relationships
# 5. Clean up temporary files

make import-data
```

## 🎨 Customization

### Adding New Pages

1. Create a new template in `templates/`
2. Add it to the build script's page templates list
3. Update navigation if needed

### Styling

- CSS is in `static/style.css`
- Uses CSS custom properties for theming
- Responsive design with mobile-first approach

### Database Schema

The database schema is defined in TrailBase migrations:

- `titles` - Movie and TV show information
- `persons` - Actor, director, and crew information
- `principals` - Cast and crew relationships
- `ratings` - User ratings and vote counts
- `episodes` - TV episode information
- `crew` - Director and writer relationships

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make all` to ensure quality
5. Submit a pull request

### Shell Script Best Practices

- Use `set -euo pipefail` for strict error handling
- Follow shellcheck recommendations
- Use meaningful variable names
- Add comments for complex logic
- Quote all variable expansions

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [IMDB](https://www.imdb.com/) for providing the dataset
- [TrailBase](https://trailbase.dev/) for the database framework
- [Alpine.js](https://alpinejs.dev/) for the reactive UI
- [shellcheck](https://www.shellcheck.net/) for shell script quality
- All contributors and maintainers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/thyme/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/thyme/discussions)
- **Documentation**: Check inline code comments and this README

---

Made with ❤️ by the Thyme community
