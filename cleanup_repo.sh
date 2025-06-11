#!/bin/bash

echo "Cleaning up LoveAndLaw Backend Repository..."
echo "==========================================="

# Remove Python cache files
echo "Removing Python cache files..."
find . -type f -name "*.pyc" -delete 2>/dev/null
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyo" -delete 2>/dev/null

# Remove test files from root directory
echo "Removing test files..."
rm -f test_*.py
rm -f check_*.py
rm -f verify_*.py

# Remove log files
echo "Removing log files..."
rm -f *.log

# Remove backup files
echo "Removing backup files..."
find . -type f -name "*.backup" -delete 2>/dev/null
find . -type f -name "*.bak" -delete 2>/dev/null
find . -type f -name "*.old" -delete 2>/dev/null
find . -type f -name "*~" -delete 2>/dev/null

# Remove OS-specific files
echo "Removing OS-specific files..."
find . -type f -name ".DS_Store" -delete 2>/dev/null
find . -type f -name "Thumbs.db" -delete 2>/dev/null

# Remove editor swap files
echo "Removing editor swap files..."
find . -type f -name "*.swp" -delete 2>/dev/null
find . -type f -name "*.swo" -delete 2>/dev/null
find . -type f -name ".*.swp" -delete 2>/dev/null

# Remove temporary data loading scripts that were created for testing
echo "Removing temporary data scripts..."
rm -f scripts/fix_and_upload_data.py
rm -f scripts/perfect_data_upload.py

# Remove test result documentation (keep main docs)
echo "Removing test result files..."
rm -f USER_SCENARIO_RESULTS.md

# Clean up any empty directories
echo "Removing empty directories..."
find . -type d -empty -delete 2>/dev/null

echo ""
echo "Cleanup complete! ✨"
echo ""
echo "Remaining structure:"
tree -I 'venv|node_modules|.git|.data' -L 2