# Thyme - TypeScript Migration

This project has been migrated from Python to TypeScript for better type safety, modern development practices, and improved maintainability.

## 🚀 Quick Start

### Prerequisites
- **Volta** (recommended) or Node.js 20.11.0+
- npm or yarn
- SQLite3
- Git

### Setup with Volta (Recommended)

1. **Install Volta**:
   ```bash
   # macOS/Linux
   curl https://get.volta.sh | bash
   
   # Windows
   # Download from https://volta.sh/
   ```

2. **Clone and setup project**:
   ```bash
   git clone <repository-url>
   cd thyme
   
   # Volta will automatically install the correct Node.js and yarn versions
   npm install
   npm run check-deps
   npm run dev:setup
   ```

### Setup without Volta

If you prefer not to use Volta, ensure you have:
- Node.js 20.11.0+
- yarn 1.22.22+ (optional, npm works too)

```bash
git clone <repository-url>
cd thyme
npm install
npm run check-deps
npm run dev:setup
```

## 📦 Available Scripts

### Development
- `npm run dev:setup` - Complete development environment setup
- `npm run check-deps` - Check system dependencies
- `npm run test` - Run tests and validation
- `npm run type-check` - TypeScript type checking
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix linting issues
- `npm run format` - Format code with Prettier

### Build & Import
- `npm run build` - Build static site
- `npm run build:watch` - Build with file watching
- `npm run import:data` - Import full IMDB dataset
- `npm run import:test` - Import limited dataset (1000 entries)

### Testing
- `npm run test:search` - Test search functionality
- `npm run test:import` - Test import process

### Cleanup
- `npm run clean` - Clean build artifacts
- `npm run clean:all` - Clean everything including database

## 🔄 Migration Summary

### What Changed
- **Language**: Python → TypeScript
- **Build System**: Makefile → npm scripts
- **Package Management**: pip → npm/yarn
- **Version Management**: Manual → Volta
- **Type Safety**: mypy → TypeScript compiler
- **Linting**: flake8 → ESLint
- **Formatting**: black → Prettier
- **Template Engine**: Jinja2 → Custom simple engine

### Scripts Converted
- `build.py` → `scripts/build.ts`
- `sql_queries.py` → `scripts/sql-queries.ts`
- `test_search.py` → `scripts/test-search.ts`
- `run_tests.py` → `scripts/test.ts`

### Benefits
- ✅ **Type Safety**: Catch errors at compile time
- ✅ **Modern JavaScript**: ES modules, async/await
- ✅ **Better Tooling**: ESLint, Prettier, TypeScript
- ✅ **Consistent Environment**: All tools in Node.js ecosystem
- ✅ **Better IDE Support**: IntelliSense, refactoring
- ✅ **Faster Development**: Hot reload, better debugging
- ✅ **Version Management**: Volta ensures consistent Node.js/yarn versions

## 🛠️ Development Workflow

1. **Start Development**:
   ```bash
   npm install
   npm run dev:setup
   ```

2. **Import Data**:
   ```bash
   npm run import:test  # For testing
   npm run import:data  # For full dataset
   ```

3. **Build Site**:
   ```bash
   npm run build
   npm run build:watch  # For development
   ```

4. **Code Quality**:
   ```bash
   npm run lint
   npm run format
   npm run type-check
   ```

## 📁 Project Structure

```
thyme/
├── scripts/           # TypeScript scripts
│   ├── build.ts      # Static site builder
│   ├── import-imdb.ts # Data import (TODO)
│   ├── test.ts       # Test runner
│   └── sql-queries.ts # SQL query loader
├── traildepot/        # TrailBase configuration
├── templates/         # HTML templates
├── static/           # CSS, JS, images
├── sql/              # SQL query files
├── package.json      # Dependencies and scripts (with Volta config)
├── tsconfig.json     # TypeScript configuration
├── .eslintrc.json    # ESLint configuration
└── .prettierrc       # Prettier configuration
```

## 🔧 Configuration Files

- **package.json**: Dependencies, scripts, and Volta configuration
- **tsconfig.json**: TypeScript compiler options
- **.eslintrc.json**: Code linting rules
- **.prettierrc**: Code formatting rules

## 🎯 Volta Configuration

The project uses Volta to ensure consistent Node.js and yarn versions:

```json
{
  "volta": {
    "node": "20.11.0",
    "yarn": "1.22.22"
  }
}
```

When you run `npm install` or `yarn install`, Volta will automatically:
- Install Node.js 20.11.0 if not already installed
- Install yarn 1.22.22 if not already installed
- Switch to the correct versions for this project

## 🚧 TODO

- [ ] Convert `import_imdb_sqlite.py` to TypeScript
- [ ] Add comprehensive test suite
- [ ] Implement proper template inheritance
- [ ] Add database migration scripts
- [ ] Create development server with hot reload

## 📚 Help

```bash
npm run help    # Show all available commands
npm run info    # Show project information
```

## 🔄 From Makefile to npm

| Makefile Command | npm Script |
|------------------|------------|
| `make help` | `npm run help` |
| `make test` | `npm run test` |
| `make build` | `npm run build` |
| `make import-data` | `npm run import:data` |
| `make clean` | `npm run clean` |
| `make check-deps` | `npm run check-deps` |

## 🆚 Volta vs Other Tools

| Feature | Volta | nvm | Manual |
|---------|-------|-----|--------|
| **Automatic switching** | ✅ | ❌ | ❌ |
| **Cross-platform** | ✅ | ❌ | ✅ |
| **Package manager support** | ✅ | ❌ | ❌ |
| **Project-specific config** | ✅ | ❌ | ❌ |
| **Zero-config setup** | ✅ | ❌ | ❌ |

Volta is recommended because it:
- Automatically switches Node.js versions per project
- Manages both Node.js and package managers (npm/yarn)
- Works seamlessly across different projects
- Requires no manual version management 