#!/bin/bash

# Railway deployment script for Tarot Agent Backend
# This script starts the FastAPI backend application

set -e  # Exit on error

echo "🚀 Starting Tarot Agent Backend..."

# Navigate to backend directory
cd backend

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing Python dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Install dependencies from pyproject.toml if it exists (using uv if available, otherwise pip)
if [ -f "pyproject.toml" ]; then
    if command -v uv &> /dev/null; then
        echo "📦 Installing dependencies using uv..."
        uv sync
    else
        echo "📦 Installing dependencies using pip..."
        pip install --no-cache-dir -e .
    fi
fi

# Get port from Railway environment variable, default to 8000
PORT=${PORT:-8000}

echo "🌐 Starting server on port $PORT..."

# Start the FastAPI application using uvicorn
# Use 0.0.0.0 to bind to all interfaces (required for Railway)
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1

