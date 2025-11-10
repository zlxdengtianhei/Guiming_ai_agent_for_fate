#!/bin/bash

# Railway deployment script for Tarot Agent Backend
# This script starts the FastAPI backend application
# Dependencies should already be installed during build phase

set -e  # Exit on error

echo "🚀 Starting Tarot Agent Backend..."

# Navigate to backend directory
cd backend || { echo "❌ Backend directory not found"; exit 1; }

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed"
    exit 1
fi

# Verify uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
    echo "❌ uvicorn is not installed. Installing dependencies..."
    pip install --no-cache-dir -r requirements.txt || pip install --no-cache-dir -r backend/requirements.txt
fi

# Get port from Railway environment variable, default to 8000
PORT=${PORT:-8000}

echo "🌐 Starting server on port $PORT..."

# Start the FastAPI application using uvicorn
# Use 0.0.0.0 to bind to all interfaces (required for Railway)
exec uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1

