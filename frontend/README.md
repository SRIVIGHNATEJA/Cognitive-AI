# Cognitive AI Learning Platform - Frontend

Streamlit-based frontend for the Cognitive AI Learning Platform.

## Prerequisites

- Python 3.10+
- Backend running on `http://localhost:8000`
- Ollama running locally with qwen2.5:1.5b model

## Installation

```bash
cd frontend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env` with your settings (default values should work for local development).

## Running the Frontend

```bash
streamlit run app.py
```

The frontend will be available at `http://localhost:8501`

## Project Structure

```
frontend/
├── app.py                    # Main entry point
├── config.py                 # Configuration
├── pages/                    # Streamlit pages
│   ├── 1_📤_Input.py
│   ├── 2_🗺️_Roadmap.py
│   ├── 3_📚_Content.py
│   ├── 4_📝_Quiz.py
│   ├── 5_📊_Analytics.py
│   └── 6_❓_Doubt.py
├── services/                 # API client services
│   ├── api_client.py
│   ├── input_service.py
│   ├── roadmap_service.py
│   ├── content_service.py
│   ├── quiz_service.py
│   ├── analytics_service.py
│   ├── doubt_service.py
│   └── session_service.py
├── components/               # Reusable UI components
│   ├── loading_spinner.py
│   ├── error_display.py
│   ├── module_card.py
│   ├── quiz_question.py
│   └── progress_bar.py
└── utils/                    # Utility functions
    ├── state_manager.py
    ├── validators.py
    └── formatters.py
```

## Features

- **Input Management**: Upload files or submit text
- **Roadmap Visualization**: View generated learning roadmap
- **Content Display**: Access notes and cheat sheets
- **Quiz System**: Take quizzes with timer support
- **Analytics Dashboard**: Track progress and weak areas
- **Doubt Resolution**: Ask questions about modules

## Development

This frontend directly consumes the FastAPI backend REST APIs. No middleware or additional services are required.

## Notes

- Backend must be running before starting the frontend
- All state is managed through Streamlit session state
- Backend session persists across browser refreshes
- Quiz timer is frontend-only (backend accepts all submissions)
