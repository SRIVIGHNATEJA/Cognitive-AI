# 🚀 Quick Start - Cognitive AI Learning Platform

## Two Commands to Run Everything

### Terminal 1 - Backend
```bash
./run.sh
```
Wait for: `Uvicorn running on http://0.0.0.0:8000`

### Terminal 2 - Frontend
```bash
./start_frontend.sh
```
Browser opens automatically to `http://localhost:8501`

---

## ✅ What's Ready

- **Phase 1 Complete**: Foundation with 23 files
- **Shared venv**: Both backend and frontend use `./venv/`
- **All dependencies installed**: FastAPI, Streamlit, pandas, plotly, etc.
- **Backend**: 254 tests passing, production-ready
- **Frontend**: Navigation skeleton with 6 pages

---

## 🔍 Verify Everything Works

### 1. Check Backend
```bash
curl http://localhost:8000/
```
Should return welcome message

### 2. Check Frontend
Open browser to `http://localhost:8501`
- Sidebar shows "✅ Connected to backend"
- Click "🏥 Check Backend Health" → Success
- Navigate through 6 pages (placeholders for now)

### 3. Run Tests
```bash
# Backend imports
./venv/bin/python test_backend_imports.py

# Frontend Phase 1
./venv/bin/python frontend/test_phase1.py
```

---

## 📁 Project Structure

```
.
├── venv/                    # Shared virtual environment
├── app/                     # Backend (FastAPI)
│   ├── main.py
│   ├── routers/
│   ├── services/
│   └── models.py
├── frontend/                # Frontend (Streamlit)
│   ├── app.py              # Main entry point
│   ├── pages/              # 6 page files
│   ├── services/           # API client
│   ├── components/         # Reusable UI
│   └── utils/              # Helpers
├── run.sh                   # Start backend
└── start_frontend.sh        # Start frontend
```

---

## 🎯 Next Steps

**Phase 2** (4-5 hours):
- Implement Input page (file upload, text input)
- Implement Roadmap page (generate, view modules)
- Implement Content page (notes, cheat sheets)

**Phase 3** (3-4 hours):
- Implement Quiz page with timer

**Phase 4** (2-3 hours):
- Implement Analytics and Doubt pages

**Phase 5** (2-3 hours):
- Polish and testing

---

## 📚 Documentation

- **STARTUP_GUIDE.md** - Detailed startup instructions
- **SHARED_VENV_EXPLANATION.md** - Why shared venv works
- **PHASE1_COMPLETION_REPORT.md** - Complete Phase 1 details
- **IMPLEMENTATION_READINESS_CHECKLIST.md** - Full checklist

---

## 🆘 Troubleshooting

**Backend won't start:**
```bash
# Check if port 8000 is in use
lsof -ti:8000 | xargs kill -9
./run.sh
```

**Frontend won't start:**
```bash
# Verify venv is activated
source venv/bin/activate
cd frontend
streamlit run app.py
```

**Can't connect:**
- Ensure backend is running first
- Check `http://localhost:8000/` in browser
- Look for errors in backend terminal

---

## ✨ Key Features

- **Backend**: 23 API endpoints, LLM integration, caching
- **Frontend**: Session management, error handling, loading states
- **Shared venv**: One environment for everything
- **Auto-reload**: Both backend and frontend reload on changes

---

## 🎉 You're Ready!

Run the two commands above and start developing!
