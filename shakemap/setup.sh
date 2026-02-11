#!/bin/bash

# Quick setup and test script for Earthquake ShakeMap System

set -e

echo "=========================================="
echo "Earthquake ShakeMap System - Quick Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "\n${YELLOW}[1/5] Checking Python environment...${NC}"
python3 --version
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

echo -e "\n${YELLOW}[2/5] Creating virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

echo -e "\n${YELLOW}[3/5] Activating virtual environment and installing dependencies...${NC}"
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "\n${YELLOW}[4/5] Creating example earthquake dataset...${NC}"
python -c "from generate_example_data import create_example_dataset; create_example_dataset()"

echo -e "\n${YELLOW}[5/5] Generating test ShakeMaps...${NC}"
python main.py -m test

echo -e "\n${GREEN}=========================================="
echo "✓ Setup complete!"
echo "==========================================${NC}"

echo -e "\n${GREEN}Generated files:${NC}"
echo "  📊 Static ShakeMaps: outputs/test_maps/*_shakemap.png"
echo "  🗺️  Interactive Maps: outputs/test_maps/*_interactive.html"
echo "  📈 Comparison Map: outputs/test_maps/all_events_comparison.html"

echo -e "\n${YELLOW}🔹 IMPORTANT: Activate virtual environment in future sessions:${NC}"
echo "  source venv/bin/activate"

echo -e "\n${GREEN}To process your own data, use:${NC}"
echo "  source venv/bin/activate && python main.py -m batch -d /path/to/earthquake/files"

echo -e "\n${GREEN}To process downloaded ShakeMaps:${NC}"
echo "  source venv/bin/activate && python main.py -m downloads"

echo -e "\n${GREEN}For more information, see README.md${NC}\n"
