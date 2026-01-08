#!/bin/bash
# Start the frontend using the shared venv

# Activate virtual environment
source venv/bin/activate

# Navigate to frontend and start Streamlit
cd frontend
streamlit run app.py
