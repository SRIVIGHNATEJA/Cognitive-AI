#!/bin/bash
# Quick start script for Cognitive AI Learning Platform

# Activate virtual environment
source venv/bin/activate

# Run the application using Python module syntax to ensure proper imports
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log --reload --reload-dir app
