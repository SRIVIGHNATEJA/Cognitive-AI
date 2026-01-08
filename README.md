# Cognitive AI Learning Platform

A backend-first, offline-first system designed for personalized college learning. The platform processes educational materials and generates learning roadmaps, content summaries, quizzes, and progress analytics using a local LLM (Ollama with qwen2.5:1.5b).

## Features

- **Input Processing**: Upload PDFs, PPTs, DOCs, or provide direct text input
- **Roadmap Generation**: AI-generated module-wise learning paths
- **Content Generation**: Detailed notes and concise cheat sheets
- **Quiz System**: MCQ assessments with automatic grading
- **Progress Analytics**: Track learning progress and identify weak areas
- **Doubt Resolution**: Context-aware Q&A for module content
- **Session Management**: Persistent state across browser refreshes
- **Offline Operation**: Complete functionality without cloud dependencies

## Prerequisites

- Python 3.10 or higher
- [Ollama](https://ollama.ai/) installed and running
- qwen2.5:1.5b model pulled in Ollama

### Installing Ollama and Model

```bash
# Install Ollama (macOS)
brew install ollama

# Start Ollama service
ollama serve

# Pull the required model (in a new terminal)
ollama pull qwen2.5:1.5b
```

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd cognitive-learning-platform
```

2. **Create and activate virtual environment**:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Configure environment** (optional):
```bash
cp .env.example .env
# Edit .env with your preferred settings
```

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run with auto-reload
python app/main.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage Example

Here's a typical workflow using the API:

### 1. Upload Learning Material

```bash
# Upload a PDF file
curl -X POST "http://localhost:8000/api/input/upload" \
  -F "file=@syllabus.pdf"

# Or submit text directly
curl -X POST "http://localhost:8000/api/input/text" \
  -H "Content-Type: application/json" \
  -d '{"text": "Machine Learning: supervised learning, neural networks..."}'
```

### 2. Generate Learning Roadmap

```bash
curl -X POST "http://localhost:8000/api/roadmap/generate" \
  -H "Content-Type: application/json" \
  -d '{"input_id": "input_abc123", "mode": "untimed"}'
```

### 3. Generate Study Materials

```bash
# Generate detailed notes
curl -X POST "http://localhost:8000/api/content/notes/module_001"

# Generate cheat sheet
curl -X POST "http://localhost:8000/api/content/cheatsheet/module_001"
```

### 4. Take a Quiz

```bash
# Generate quiz
curl -X POST "http://localhost:8000/api/quiz/generate/module_001" \
  -H "Content-Type: application/json" \
  -d '{"mode": "untimed"}'

# Submit answers
curl -X POST "http://localhost:8000/api/quiz/submit/module_001" \
  -H "Content-Type: application/json" \
  -d '{"quiz_id": "quiz_xyz", "answers": {"1": "A", "2": "B", ...}}'
```

### 5. Track Progress

```bash
# Get overall analytics
curl "http://localhost:8000/api/analytics/overview"

# Identify weak areas
curl "http://localhost:8000/api/analytics/weak-areas"
```

### 6. Ask Questions

```bash
curl -X POST "http://localhost:8000/api/doubt/ask" \
  -H "Content-Type: application/json" \
  -d '{"module_id": "module_001", "question": "What is backpropagation?"}'
```

For interactive API exploration, visit http://localhost:8000/docs

## Project Structure

```
.
├── app/                       # Application code
│   ├── __init__.py
│   ├── main.py               # FastAPI application
│   ├── config.py             # Configuration settings
│   ├── logging_config.py     # Logging setup
│   ├── models.py             # Pydantic models
│   ├── routers/              # API endpoints
│   │   ├── input.py          # Input processing
│   │   ├── roadmap.py        # Roadmap generation
│   │   ├── content.py        # Content generation
│   │   ├── quiz.py           # Quiz system
│   │   ├── analytics.py      # Analytics
│   │   ├── doubt.py          # Doubt resolution
│   │   └── session.py        # Session management
│   └── services/             # Business logic
│       ├── input_service.py
│       ├── roadmap_service.py
│       ├── content_service.py
│       ├── quiz_service.py
│       ├── analytics_service.py
│       ├── doubt_service.py
│       ├── session_service.py
│       ├── llm_service.py    # Ollama integration
│       ├── llm_schemas.py    # LLM output schemas
│       ├── cache_service.py  # File-based caching
│       └── file_processor.py # File extraction
├── tests/                    # Test suite
│   ├── unit/                # Unit tests (186 tests)
│   ├── property/            # Property-based tests (5 tests)
│   └── integration/         # Integration tests (48 tests)
├── cache/                   # File-based cache storage
│   ├── input/              # Processed input files
│   ├── roadmap/            # Generated roadmaps
│   ├── content/            # Notes and cheat sheets
│   ├── quizzes/            # Quiz Q&As and metrics
│   ├── analytics/          # Analytics data
│   └── session.json        # Session state
├── requirements.txt        # Python dependencies
├── pytest.ini             # Pytest configuration
├── .env.example           # Environment variables template
└── README.md              # This file
```

## API Endpoints

### System Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

### Input Processing

- `POST /api/input/upload` - Upload file (PDF, PPT, PPTX, DOC, DOCX)
- `POST /api/input/text` - Submit text input directly
- `GET /api/input/status` - Get input processing status

### Roadmap Generation

- `POST /api/roadmap/generate` - Generate learning roadmap from input
- `GET /api/roadmap` - Retrieve cached roadmap
- `DELETE /api/roadmap` - Reset roadmap cache

### Content Generation

- `POST /api/content/notes/{module_id}` - Generate detailed notes for a module
- `GET /api/content/notes/{module_id}` - Retrieve cached notes
- `POST /api/content/cheatsheet/{module_id}` - Generate cheat sheet for a module
- `GET /api/content/cheatsheet/{module_id}` - Retrieve cached cheat sheet

### Quiz System

- `POST /api/quiz/generate/{module_id}` - Generate quiz for a module
- `POST /api/quiz/submit/{module_id}` - Submit quiz answers for evaluation
- `GET /api/quiz/history/{module_id}` - Get last 2 quiz Q&As for a module
- `GET /api/quiz/metrics/{module_id}` - Get quiz performance metrics

### Analytics & Progress

- `GET /api/analytics/overview` - Get overall learning progress
- `GET /api/analytics/module/{module_id}` - Get module-specific analytics
- `GET /api/analytics/weak-areas` - Identify modules needing attention

### Doubt Resolution

- `POST /api/doubt/ask` - Ask questions about module content

### Session Management

- `GET /api/session` - Get current session state
- `POST /api/session/reset` - Reset session and clear state

## Testing

The project has comprehensive test coverage with 248 tests across three categories:

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test types:
```bash
# Unit tests only (186 tests)
pytest tests/unit/

# Property-based tests only (5 tests)
pytest tests/property/

# Integration tests only (48 tests)
pytest tests/integration/
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

Run specific test file:
```bash
pytest tests/unit/test_llm_service.py -v
```

### Test Categories

- **Unit Tests**: Test individual functions and methods in isolation
- **Property-Based Tests**: Use Hypothesis to test universal properties across many inputs
- **Integration Tests**: Test complete API flows end-to-end

## Configuration

All configuration is managed through environment variables with the `APP_` prefix. See `.env.example` for available options.

Key settings:
- `APP_OLLAMA_BASE_URL`: Ollama service URL (default: http://localhost:11434)
- `APP_OLLAMA_MODEL`: LLM model to use (default: qwen2.5:1.5b)
- `APP_MAX_FILE_SIZE_MB`: Maximum upload file size (default: 10MB)
- `APP_CACHE_DIR`: Cache directory location (default: cache)
- `APP_LOG_LEVEL`: Logging level (default: INFO)

## Development

### Adding New Features

1. Create service module in `app/services/`
2. Create router module in `app/routers/`
3. Register router in `app/main.py`
4. Add tests in appropriate test directory
5. Update documentation

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Document all public APIs with docstrings
- Keep functions focused and testable

## Architecture

The system follows a modular, service-oriented architecture:

- **API Layer**: FastAPI routers handling HTTP requests
- **Service Layer**: Business logic and LLM integration
- **Data Layer**: Pydantic models and file-based caching
- **LLM Service**: Isolated Ollama integration

All LLM interactions are centralized in a single service module for maintainability.

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please [open an issue](link-to-issues).
