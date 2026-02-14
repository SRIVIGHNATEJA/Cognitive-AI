# Model Comparison Module

## Overview

This module provides a systematic framework for comparing multiple LLM models on both **performance** and **accuracy** metrics. It reuses existing benchmark and golden test logic without code duplication.

## Purpose

When deploying an AI-powered learning platform, choosing the right LLM model is critical. This module helps answer:

- Which model provides the best balance of speed and accuracy?
- Which model uses the least memory?
- Which model produces the most accurate educational content?
- Which model is most resistant to hallucinations?

## Hardware Context

All benchmarks were conducted on:
- **Device**: 8GB Mac M3
- **OS**: macOS
- **LLM Runtime**: Ollama

This controlled environment ensures fair comparison across models.

## Metrics Measured

### Performance Metrics (Roadmap Generation Task)
- **Cold Time**: Execution time with fresh cache (seconds)
- **Warm Time**: Execution time with populated cache (seconds)
- **Peak RAM**: Maximum memory usage during execution (MB)

### Accuracy Metrics (Golden Set Tests)
- **Syllabus Adherence**: Coverage of expected topics (%)
- **Concept Accuracy**: Presence of expected concepts, absence of forbidden ones (%)
- **Hallucination Resistance**: Avoidance of fabricated information (%)
- **JSON Compliance**: Structural correctness of generated quizzes (%)

## Experimental Design

### Controlled Variables
- Same test input data across all models
- Same hardware and runtime environment
- Same benchmark configuration
- Isolated cache per test (no cross-contamination)

### Test Sequence
For each model:
1. Override `settings.ollama_model` temporarily
2. Run performance subset (roadmap generation: 1 cold + 1 warm)
3. Run accuracy tests (full golden set: 20 test cases)
4. Restore original model setting
5. Save results incrementally to CSV

### Important Constraints
- **One model at a time**: Models are NOT run in parallel
- **No production impact**: Original model setting is always restored
- **No code duplication**: Reuses existing benchmark and test logic
- **Incremental logging**: Results saved after each model completes

## Usage

### Prerequisites

Ensure all models you want to compare are pulled:

```bash
ollama pull llama3.2:3b
ollama pull mistral:7b
ollama pull phi3:mini
```

### Running Comparison

1. Edit `model_comparator.py` to specify models:

```python
models_to_compare = [
    "llama3.2:3b",
    "mistral:7b",
    "phi3:mini",
]
```

2. Execute from project root:

```bash
PYTHONPATH=. python evaluation/model_comparison/model_comparator.py
```

3. Results are saved to `evaluation/model_comparison/comparison_results.csv`

### Output Format

CSV columns:
- `model_name`: Model identifier
- `cold_time_seconds`: Cold run execution time
- `warm_time_seconds`: Warm run execution time
- `peak_ram_mb`: Peak memory usage
- `syllabus_adherence_percent`: Topic coverage rate
- `concept_accuracy_percent`: Concept correctness rate
- `hallucination_pass_percent`: Hallucination resistance rate
- `json_compliance_percent`: JSON structure compliance rate
- `timestamp`: Test execution timestamp

### Example Output

```
Model                Cold (s)   Warm (s)   RAM (MB)   Syllabus   Concept    Halluc     JSON      
--------------------------------------------------------------------------------
llama3.2:3b          45.2       38.1       650        88.0       80.0       100.0      100.0     
mistral:7b           52.3       44.7       820        92.0       85.0       100.0      100.0     
phi3:mini            38.9       32.4       480        84.0       75.0       95.0       100.0     
```

## Architecture

### File Structure

```
evaluation/model_comparison/
├── model_comparator.py      # Main comparison orchestrator
├── comparison_results.csv   # Output CSV (generated on first run)
└── README.md                # This file
```

### Design Principles

1. **No Duplication**: Imports and reuses existing logic from:
   - `evaluation.benchmark_runner` (performance benchmarks)
   - `evaluation.golden_tests.golden_test_runner` (accuracy tests)

2. **Minimal Subset**: Only runs roadmap generation for performance (fastest task)

3. **Isolation**: Uses `CacheIsolation` context manager to prevent cache pollution

4. **Restoration**: Always restores `settings.ollama_model` after each test

5. **Incremental Saving**: Writes results after each model completes (safe for interruption)

## Interpretation Guide

### Performance Metrics
- **Lower cold/warm time** = Faster inference
- **Lower peak RAM** = More memory-efficient
- **Smaller cold-warm gap** = Better cache utilization

### Accuracy Metrics
- **Higher syllabus adherence** = Better topic coverage
- **Higher concept accuracy** = More precise content generation
- **Higher hallucination resistance** = More reliable information
- **Higher JSON compliance** = Better structured output

### Trade-offs
- Larger models (7B+) typically have higher accuracy but slower speed
- Smaller models (3B) are faster but may sacrifice some accuracy
- Memory usage correlates with model size

## Extending the Module

### Adding More Models

Edit `models_to_compare` list in `model_comparator.py`:

```python
models_to_compare = [
    "llama3.2:3b",
    "llama3.2:7b",
    "mistral:7b",
    "phi3:mini",
    "gemma:7b",
]
```

### Adding More Performance Tasks

Modify `run_performance_subset()` to include additional benchmarks:

```python
# Import additional benchmark functions
from evaluation.benchmark_runner import (
    benchmark_roadmap_generation,
    benchmark_notes_generation,
    benchmark_quiz_generation,
)

# Run multiple tasks
cold_roadmap = benchmark_roadmap_generation(test_data, 1, "cold")
cold_notes = benchmark_notes_generation(test_data, 1, "cold")
```

### Customizing Accuracy Tests

Modify `run_accuracy_tests()` to run subset of golden tests:

```python
# Run only specific test types
runner.test_syllabus_adherence(test_case)
runner.test_hallucination_resistance(test_case)
```

## Troubleshooting

### Model Not Found
```
Error: model 'mistral:7b' not found
```
**Solution**: Pull the model first: `ollama pull mistral:7b`

### Out of Memory
```
Error: failed to allocate memory
```
**Solution**: Test smaller models or close other applications

### Import Errors
```
Error: Cannot import evaluation modules
```
**Solution**: Run from project root with `PYTHONPATH=.`

## Future Enhancements

Potential improvements:
- Add statistical significance testing (t-tests, confidence intervals)
- Support for parallel model execution (if hardware allows)
- Visualization dashboard (charts, graphs)
- Cost analysis (inference time × compute cost)
- A/B testing framework for production deployment

## References

- Phase 1: Performance Benchmark Harness (`evaluation/benchmark_runner.py`)
- Phase 2: Golden Set Testing (`evaluation/golden_tests/`)
- Phase 3: Model Comparison (this module)
