# Cognitive AI Learning Platform - Startup Guide

## ✅ Shared Virtual Environment

**Good news!** Both backend and frontend use the **same venv** - no need for separate environments.

All dependencies (FastAPI, Streamlit, etc.) are installed in `./venv/`

## Quick Start

### 1. Start the Backend

Open a terminal and run:

```bash
./run.sh
```

The backend will start on `http://localhost:8000`

You should see output like:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Keep this terminal open** - the backend needs to stay running.

### 2. Start the Frontend

Open a **new terminal** (keep the backend running) and run:

```bash
./start_frontend.sh
```

Or manually:
```bash
source venv/bin/activate
cd frontend
streamlit run app.py
```

The frontend will start on `http://localhost:8501`

Your browser should automatically open to the app.

---

## Troubleshooting

### Backend Won't Start

**Error: `ModuleNotFoundError: No module named 'app'`**

Solution: The `run.sh` script has been updated. Make sure you're using the latest version:

```bash
#!/bin/bash
# Quick start script for Cognitive AI Learning Platform

# Activate virtual environment
source venv/bin/activate

# Run the application using Python module syntax to ensure proper imports
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Error: `No module named 'pypdf'` or other missing modules**

Solution: Install backend dependencies:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Error: Port 8000 already in use**

Solution: Kill the existing process:

```bash
lsof -ti:8000 | xargs kill -9
```

Then restart the backend.

### Frontend Won't Start

**Error: `No module named 'streamlit'`**

Solution: Frontend dependencies are now installed in the shared venv. Just use:

```bash
./start_frontend.sh
```

Or activate the venv first:
```bash
source venv/bin/activate
cd frontend
streamlit run app.py
```

**Error: Cannot connect to backend**

Solution: Make sure the backend is running first. Check:

```bash
curl http://localhost:8000/
```

Should return:
```json
{
  "message": "Welcome to Cognitive AI Learning Platform",
  "version": "1.0.0",
  "docs": "/docs",
  "redoc": "/redoc"
}
```

---

## Verification

### Backend Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "Cognitive AI Learning Platform",
  "version": "1.0.0"
}
```

### Frontend Phase 1 Test

```bash
python frontend/test_phase1.py
```

Expected: All 6 tests pass

---

## Manual Startup (Alternative)

If `run.sh` doesn't work, you can start manually:

### Backend (Manual)

```bash
# Activate venv
source venv/bin/activate

# Start uvicorn
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend (Manual)

```bash
# Navigate to frontend
cd frontend

# Start streamlit
streamlit run app.py
```

---

## What to Expect

### Backend (Terminal 1)

You'll see:
- Startup logs
- Session initialization
- Cache directory verification
- Server ready message

### Frontend (Terminal 2 + Browser)

You'll see:
- Streamlit starting
- Browser opens automatically
- Welcome page with navigation
- Sidebar with session info

---

## Phase 1 Status

✅ **Phase 1 Complete** - Foundation is ready

Current functionality:
- Backend connectivity
- Session management
- Navigation skeleton
- 6 page placeholders

**Next:** Phase 2 will implement Input, Roadmap, and Content pages.

---

## Need Help?

1. Check both terminals for error messages
2. Verify backend is running: `curl http://localhost:8000/`
3. Check frontend test: `python frontend/test_phase1.py`
4. Review logs in both terminals

---

## Stopping the Application

### Stop Frontend
Press `Ctrl+C` in the frontend terminal

### Stop Backend
Press `Ctrl+C` in the backend terminal

Or kill the process:
```bash
lsof -ti:8000 | xargs kill -9
```

---

## Development Workflow

1. **Backend changes**: The backend runs with `--reload`, so it will auto-restart on code changes
2. **Frontend changes**: Streamlit auto-reloads when you save files
3. **Keep both terminals visible** to see logs and errors

---

## URLs

- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Next Steps

Once both are running:

1. Open http://localhost:8501 in your browser
2. Check the sidebar shows "✅ Connected to backend"
3. Click "🏥 Check Backend Health" - should show success
4. Navigate through the 6 pages (they're placeholders for now)
5. Ready for Phase 2 implementation!
