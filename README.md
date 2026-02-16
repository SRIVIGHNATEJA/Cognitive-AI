<div align="center">
  <h1>🧠 Cognitive AI Assistant</h1>
  <p><b>Enterprise-Grade, Zero-Cloud LLM Orchestration & Learning Engine</b></p>
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](#)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.103.2-009688?logo=fastapi&logoColor=white)](#)
  [![Streamlit](https://img.shields.io/badge/Streamlit-1.27.0-FF4B4B?logo=streamlit&logoColor=white)](#)
  [![Ollama](https://img.shields.io/badge/Ollama-Edge_Inference-black?logo=ollama&logoColor=white)](#)
  [![Pytest](https://img.shields.io/badge/Pytest-334_Tests-green?logo=pytest&logoColor=white)](#)
</div>

---

> **The Challenge:** Traditional digital learning is passive. Conversational LLMs are prone to hallucination, context drift, and expose sensitive user intellectual property to cloud APIs.
> 
> **The Solution:** An offline-first, edge-compute orchestration platform that autonomously converts unstructured documents (PDF, DOCX) into strict, DAG-validated learning roadmaps with active recall testing—operating entirely without cloud dependencies.

---

## 🚀 Business Value & Technical Impact

Designed for environments with strict data governance and privacy requirements, this platform demonstrates how targeted Small Language Models (SLMs) can outperform generic cloud APIs when paired with rigorous backend orchestration.

*   **100% Data Privacy:** Zero data leaves the host machine; entirely air-gappable.
*   **Cost Efficiency:** $0 recurring API costs via edge-compute inference.
*   **High-Performance Caching:** Architectural separation of quiz generation and evaluation reduces feedback latency by **>5,000x** (6.1s → <1ms).
*   **Deterministic Integrity:** 100% JSON schema compliance and 92% syllabus adherence achieved through engineered constraints, outperforming unconstrained conversational models.

---

## 🏗️ System Architecture & Orchestration

The platform implements a decoupled, 3-tier microservice architecture to orchestrate the **Cognitive Reinforcement Cycle** (Study → Test → Evaluate → Retry).

```mermaid
flowchart LR
    subgraph InputLayer ["Input Layer"]
    A["Raw Material\n(PDF/DOCX/PPT)"] --> B["Ingestion\n& Normalization"]
    end
    
    subgraph OrchestrationEngine ["Orchestration Engine (FastAPI)"]
    B --> C["DAG Roadmap\nGenerator"]
    C --> D["Content\nSynthesis"]
    D --> E["Adaptive Quiz\nGenerator"]
    end
    
    subgraph EdgeInference ["Edge Inference (Ollama)"]
    C <--> M["qwen2.5:1.5b\n(Edge SLM)"]
    D <--> M
    E <--> M
    end
    
    subgraph StateManagement ["State Management"]
    E --> F["Deferred\nEvaluation Cache"]
    F --> G["Analytics &\nWeak Area Detection"]
    end
```

### Key Engineering Decisions

#### 1. "Deferred Assessment" Engine (Latency & Security)
Traditional LLM applications generate questions and answers synchronously, risking client-side data leakage and causing high initial latency. This system implements a proprietary **Deferred Assessment** pattern.

```mermaid
sequenceDiagram
    participant UI as Client Interface
    participant API as FastAPI Backend
    participant Cache as State Manager
    participant LLM as Inference Engine

    Note over UI,LLM: Step 1: Initial Generation
    UI->>API: Generate Quiz (Topic)
    API->>LLM: Prompt (Questions ONLY)
    LLM-->>API: 5 MCQs (No Answers)
    API->>Cache: Store Active Quiz State
    API-->>UI: Render Quiz

    Note over UI,LLM: Step 2: First Evaluation (Cache Miss)
    UI->>API: Submit Answers
    API->>LLM: Evaluate & Explain
    LLM-->>API: Correct Answers & Logic
    API->>Cache: Persist Evaluation Keys
    API-->>UI: Display Results

    Note over UI,LLM: Step 3: Retry (Cache Hit)
    UI->>API: Retry Quiz
    API->>Cache: Load Evaluation Keys
    Note right of API: Latency drops from ~6.1s to <1ms
    API-->>UI: Instant Re-Evaluation
```

#### 2. Topological DAG for Curriculum Integrity
To prevent hallucinated dependencies or circular prerequisite loops, the roadmap generator does not trust the LLM with state management. Instead, it parses the LLM's raw topic output and builds a **Topological Directed Acyclic Graph (DAG)**, using deterministic SHA-256 hashes (`mod_<hash12>`) to enforce mathematically sound learning paths.

#### 3. Zero-Database Edge State
To maximize portability and reduce operational complexity, the system relies on a custom file-based JSON caching protocol with atomic writes and selective pruning. This eliminates the overhead of running PostgreSQL or Redis on edge devices while maintaining complete session state.

---

## 📊 Empirical Validation & Benchmarking

Architectural decisions in this project are driven by telemetry, not hype. A custom benchmarking harness evaluated three distinct models across 20 golden test cases under identical memory constraints.

| Evaluation Metric | `qwen2.5:1.5b` (Selected) | `llama3.2:1b` | `phi:2.7b` |
| :--- | :--- | :--- | :--- |
| **Edge RAM Footprint** | **865 MB** | 720 MB | 1457 MB |
| **Syllabus Adherence** | **92%** | 84% | 88% |
| **JSON Schema Compliance** | **100%** | 80% (Flaky) | 100% |
| **Avg Inference Latency** | **8.78s** | 7.12s | 15.87s |

**Architectural Verdict:** `qwen2.5:1.5b` was selected. Its flawless 100% JSON compliance prevented downstream application parsing crashes, making it vastly superior to the slightly faster `llama3.2:1b` for strict structured data orchestration.

---

## 🧪 Quality Assurance & CI/CD Readiness

The codebase is fortified by a rigorous **334-test** suite, ensuring enterprise-grade stability and reliability:

*   **Unit Tests (186):** Isolated validation of normalization logic, HTTP parsing, and LLM prompt schemas.
*   **Integration Tests (48):** End-to-end HTTP request-response validation via `FastAPI TestClient`.
*   **Property-Based Tests (5):** Utilizing the `Hypothesis` framework to assert mathematical invariants (e.g., *Invariant: Every generated quiz must contain exactly 5 questions; every question exactly 4 options; every prerequisite must resolve to an existing DAG node.*).

---

## 💻 Deployment & Execution

The platform is designed to deploy seamlessly on any environment with sufficient memory for SLM inference.

**Core Stack:** Python 3.10+, FastAPI, Streamlit, Pydantic v2, Pytest, Ollama.

```bash
# 1. Clone & Setup Environment
git clone https://github.com/yourusername/cognitive-ai-assistant.git
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Initialize Edge Inference Engine
ollama pull qwen2.5:1.5b

# 3. Launch the Orchestration API & Client Interface
./run.sh              # Starts Backend Orchestration API
./start_frontend.sh   # Starts Reactive Client Interface
```

*The client interface and backend API will bind to your designated secure loopback addresses automatically.*

---
<div align="center">
  <i>Developed to demonstrate rigorous systems architecture, empirical AI validation, and secure edge-compute deployment strategies.</i>
</div>
