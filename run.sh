#!/bin/bash
# Quick start script for Cognitive AI Learning Platform

# Activate virtual environment
source venv/bin/activate

# Run the application using Python module syntax to ensure proper imports
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
