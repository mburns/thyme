# Contributing to Thyme

Thank you for your interest in contributing to Thyme! This document provides guidelines and information for contributors.

## Getting Started

### Prerequisites

- Bash 4.0 or higher
- SQLite 3.39 or higher
- Git
- Make (optional, for using Makefile commands)
- shellcheck (for linting)
- shfmt (for formatting, optional)

### Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/thyme.git
   cd thyme
   ```

2. **Check system dependencies**
   ```bash
   make check-deps
   ```

3. **Set up the development environment**
   ```bash
   # Install development dependencies (pre-commit)
   make install-dev
   
   # Install pre-commit hooks
   make setup-hooks
   ```

4. **Verify the setup**
   ```bash
   make help
   ```

## Development Workflow

### Code Style

We use several tools to maintain code quality:

- **shellcheck** - Shell script linting and best practices
- **shfmt** - Shell script formatting
- **pre-commit hooks** - Automated checks before each commit
- **GitHub Actions** - Continuous integration

### Making Changes

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Follow the shell script best practices
   - Use `set -euo pipefail` for strict error handling
   - Add comments for complex logic
   - Test your changes locally

3. **Run checks before committing**
   ```bash
   make all
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add your descriptive commit message"
   ```
   
   The pre-commit hooks will automatically run checks and format your code.

### Testing

Run tests to ensure everything works correctly:

```bash
make test
```

This will:
- Check shell script syntax with shellcheck
- Verify script executability
- Test directory structure
- Validate required files exist

### Building

Test the build process:

```bash
make build
```

This will create a static site in the `dist/` directory.

### Importing Data

To test the data import functionality:

```bash
make import-data
```

**Note**: This requires the TrailBase server to be running first to create the database.

## Pull Request Process

1. **Ensure your code passes all checks**
   ```bash
   make all
   ```

2. **Update documentation** if you've added new features or changed existing behavior

3. **Create a pull request** with a clear description of your changes

4. **Wait for review** - maintainers will review your code and provide feedback

## Code Style Guidelines

### Shell Scripts

- Use `set -euo pipefail` for strict error handling
- Follow shellcheck recommendations
- Use meaningful variable names
- Add comments for complex logic
- Use local variables when possible
- Quote all variable expansions
- Use `[[ ]]` for conditional tests
- Prefer `$(command)` over backticks

### Example Shell Script Structure

```bash
#!/bin/bash

set -euo pipefail

# Script description
# Usage: script.sh [options]

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Main function
main() {
    log_info "Starting script..."
    # Your logic here
}

# Run main function
main "$@"
```

### SQL

- Use SQLFluff for formatting
- Follow consistent naming conventions
- Add comments for complex queries

### Markdown

- Use markdownlint for consistency
- Follow standard markdown conventions
- Include code examples where helpful

## Project Structure

```
thyme/
├── templates/          # HTML templates
├── static/            # Static assets (CSS, JS, images)
├── traildepot/        # TrailBase configuration and migrations
├── data/              # IMDB data files (downloaded automatically)
├── dist/              # Built static site (generated)
├── *.sh               # Shell scripts
├── .github/workflows/ # CI/CD configuration
└── docs/              # Documentation
```

## Common Commands

```bash
make help          # Show all available commands
make check-deps    # Check system dependencies
make install-dev   # Install development dependencies
make setup-hooks   # Install pre-commit hooks
make lint          # Run linting checks
make test          # Run tests
make build         # Build static site
make clean         # Clean build artifacts
make all           # Run all checks
make info          # Show project information
```

## Shell Script Best Practices

### Error Handling

```bash
# Always use strict mode
set -euo pipefail

# Handle errors gracefully
if ! command; then
    log_error "Command failed"
    exit 1
fi
```

### Variable Safety

```bash
# Always quote variables
echo "$variable"
cp "$source" "$destination"

# Use local variables in functions
my_function() {
    local temp_var
    temp_var="$(some_command)"
    echo "$temp_var"
}
```

### Conditional Tests

```bash
# Use [[ ]] instead of [ ]
if [[ -f "$file" ]]; then
    echo "File exists"
fi

# Use proper string comparisons
if [[ "$var" == "value" ]]; then
    echo "Match"
fi
```

## Getting Help

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Discussions**: Use GitHub Discussions for questions and general discussion
- **Documentation**: Check the README.md and inline code comments

## License

By contributing to Thyme, you agree that your contributions will be licensed under the MIT License.

## Code of Conduct

Please be respectful and inclusive in all interactions. We follow the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/0/code_of_conduct/). 