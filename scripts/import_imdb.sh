#!/bin/bash

# IMDB Data Import Script for TrailBase
# This script automates the process of importing IMDB data

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DATA_DIR="${PROJECT_DIR}/data"
DB_PATH="${PROJECT_DIR}/traildepot/data/main.db"
PYTHON_SCRIPT="${SCRIPT_DIR}/import_imdb.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if TrailBase is running
check_trailbase() {
    log_info "Checking if TrailBase is running..."
    
    if curl -s http://localhost:4000/_/admin/ > /dev/null 2>&1; then
        log_success "TrailBase is running on port 4000"
        return 0
    else
        log_error "TrailBase is not running on port 4000"
        log_info "Please start TrailBase with: ./trailbase run"
        return 1
    fi
}

# Check if required files exist
check_data_files() {
    log_info "Checking for IMDB data files..."
    
    required_files=(
        "name.basics.tsv.gz"
        "title.basics.tsv.gz"
        "title.episode.tsv.gz"
        "title.ratings.tsv.gz"
        "title.akas.tsv.gz"
        "title.crew.tsv.gz"
        "title.principals.tsv.gz"
    )
    
    missing_files=()
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "${DATA_DIR}/${file}" ]]; then
            missing_files+=("$file")
        fi
    done
    
    if [[ ${#missing_files[@]} -eq 0 ]]; then
        log_success "All required IMDB data files found"
        return 0
    else
        log_error "Missing required files:"
        for file in "${missing_files[@]}"; do
            echo "  - ${file}"
        done
        log_info "Please download the IMDB dataset and place the files in the ${DATA_DIR} directory"
        return 1
    fi
}

# Check Python dependencies
check_python_deps() {
    log_info "Checking Python dependencies..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        return 1
    fi
    
    # Check if required modules are available
    python3 -c "import sqlite3, json, gzip, argparse, pathlib, logging" 2>/dev/null || {
        log_error "Missing required Python modules"
        log_info "Please install required modules: pip install sqlite3 json gzip argparse pathlib logging"
        return 1
    }
    
    log_success "Python dependencies are satisfied"
    return 0
}

# Run the import
run_import() {
    log_info "Starting IMDB data import..."
    
    cd "$PROJECT_DIR"
    
    # Run the Python import script
    python3 "$PYTHON_SCRIPT" \
        --data-dir "$DATA_DIR" \
        --db-path "$DB_PATH" \
        --batch-size 1000
    
    if [[ $? -eq 0 ]]; then
        log_success "IMDB data import completed successfully!"
    else
        log_error "IMDB data import failed"
        exit 1
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -c, --check-only    Only check prerequisites, don't run import"
    echo "  -d, --data-dir DIR  Specify data directory (default: ./data)"
    echo "  -b, --batch-size N  Specify batch size (default: 1000)"
    echo ""
    echo "This script imports IMDB data into TrailBase."
    echo ""
    echo "Prerequisites:"
    echo "  1. TrailBase must be running on port 4000"
    echo "  2. IMDB dataset files must be in the data directory"
    echo "  3. Python 3 must be installed"
    echo ""
    echo "Example:"
    echo "  $0 --data-dir /path/to/imdb/data --batch-size 500"
}

# Parse command line arguments
CHECK_ONLY=false
BATCH_SIZE=1000

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--check-only)
            CHECK_ONLY=true
            shift
            ;;
        -d|--data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        -b|--batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    log_info "IMDB Data Import Script"
    log_info "========================"
    
    # Check prerequisites
    if ! check_trailbase; then
        exit 1
    fi
    
    if ! check_data_files; then
        exit 1
    fi
    
    if ! check_python_deps; then
        exit 1
    fi
    
    if [[ "$CHECK_ONLY" == "true" ]]; then
        log_success "All prerequisites are satisfied"
        exit 0
    fi
    
    # Run the import
    run_import
}

# Run main function
main "$@" 