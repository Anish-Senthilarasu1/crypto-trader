#!/bin/bash
# Development demo script - seed data and run backtest

set -e

echo "🚀 Aurora Trader - Development Demo"
echo "===================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Create data directory
mkdir -p data

# Run health check
echo ""
echo "Starting API server..."
python -m backend.main &
API_PID=$!

# Wait for API to start
sleep 3

echo ""
echo "Testing health endpoint..."
curl -s http://localhost:8000/health | python -m json.tool

echo ""
echo "✅ API is healthy!"
echo ""
echo "API running at http://localhost:8000"
echo "API PID: $API_PID"
echo ""
echo "Press Ctrl+C to stop the server"

# Wait for user interrupt
wait $API_PID
