#!/bin/bash
# Fix all logger imports

find src/agents/legal_specialists/ -name "*.py" -type f -exec sed -i '' 's/setup_logger/get_logger/g' {} \;