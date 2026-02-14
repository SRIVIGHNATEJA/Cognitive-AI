# Performance Benchmark Harness

## Purpose

This evaluation module provides an isolated performance benchmarking system for the Cognitive AI Learning Platform. It measures computational performance metrics (execution time, memory usage, CPU utilization) for core platform operations without modifying any production code.

The benchmark harness helps:
- Track performance trends over time
- Identify optimization opportunities
- Understand resource consumption patterns
- Validate system behavior under load
- Establish performance baselines

## Non-Invasive Design

**CRITICAL: No production code was modified during implementation.**

This benchmark harness is completely isolated from the production system:

- All benchmark code lives in the `/evaluation` folder
- No existing production files were modified
- No refactoring of services, routers, or frontend code
- Production system runs exactly as before
- Benchmarks import and exercise existing services without modification

**Folder Structure:**
```
evaluation/
├── benchmark_runner.py      # Main benchmark orchestrator
├── system_monitor.py         # Resource monitoring (RAM, CPU)
├── metrics_logger.py         # CSV logging functionality
├── results/
│   ├── .gitkeep             # Track empty directory
│   └── performance_log.csv  # Benchmark results (generated)
└── README.md                # This file
```

**Verification:**
```bash
# Confirm only new files in /evaluation
git status

# Should show:
# ?? evaluation/
```

## Usage

### Prerequisites

1. Ensure you're in the project root directory
2. Install required dependency:
   ```bash
   pip install psutil
   ```
3. Ensure Ollama is running with the configured model

### Running Benchmarks

Execute the benchmark suite:

```bash
python evaluation/benchmark_runner.py
```

### What Gets Benchmarked

The harness benchmarks 4 core tasks, each executed 3 times:

1. **Roadmap Generation**: Generate learning roadmap from input content
2. **Notes Generation**: Generate detailed notes for one module
3. **Quiz Generation**: Generate quiz questions for one module
4. **Quiz Evaluation**: Evaluate quiz submission (first attempt)

### Expected Duration

- Total runtime: ~5-10 minutes (depends on model and hardware)
- Each task: ~30-60 seconds per run
- 12 total benchmark runs (4 tasks × 3 repetitions)

### Console Output

During execution, you'll see:
```
================================================================================
COGNITIVE AI LEARNING PLATFORM - PERFORMANCE BENCHMARK
================================================================================
Model: qwen2.5:1.5b
Repetitions per task: 3
Results will be saved to: evaluation/results/performance_log.csv
================================================================================

Starting benchmarks...

Roadmap Generation:
  Running roadmap generation (run 1/3)...
    Completed: 32.45s
  Running roadmap generation (run 2/3)...
    Completed: 31.89s
  ...

================================================================================
BENCHMARK SUMMARY
================================================================================

Task                      Avg Time (s)    Avg RAM (MB)    Avg CPU (%)    
--------------------------------------------------------------------------------
Roadmap Generation        32.11           245.6           78.3           
Notes Generation          18.23           198.4           65.2           
Quiz Generation           25.67           210.8           72.1           
Quiz Evaluation           45.34           220.5           68.9           

--------------------------------------------------------------------------------
Peak RAM Usage: 245.60 MB
Peak CPU Usage: 78.30%
Total Benchmark Duration: 487.23s (8.1 minutes)
Model: qwen2.5:1.5b
================================================================================

✓ Benchmarks complete! Results saved to evaluation/results/performance_log.csv
```

## Output Format

### CSV File

Results are appended to `evaluation/results/performance_log.csv` with the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `task_name` | Name of the benchmarked task | `roadmap_generation` |
| `run_number` | Run number (1-3) | `1` |
| `total_time_seconds` | Total execution time in seconds | `32.45` |
| `peak_ram_mb` | Peak RAM usage in megabytes | `245.6` |
| `avg_cpu_percent` | Average CPU usage percentage | `78.3` |
| `timestamp` | ISO 8601 timestamp | `2026-02-14T10:30:45.123456` |
| `model_name` | LLM model used | `qwen2.5:1.5b` |

### Example CSV Output

```csv
task_name,run_number,total_time_seconds,peak_ram_mb,avg_cpu_percent,timestamp,model_name
roadmap_generation,1,32.45,245.6,78.3,2026-02-14T10:30:45.123456,qwen2.5:1.5b
roadmap_generation,2,31.89,243.2,76.8,2026-02-14T10:31:20.456789,qwen2.5:1.5b
roadmap_generation,3,32.34,246.1,79.1,2026-02-14T10:31:55.789012,qwen2.5:1.5b
notes_generation,1,18.23,198.4,65.2,2026-02-14T10:32:30.123456,qwen2.5:1.5b
...
```

### Data Persistence

- Results are **appended** to the CSV file (not overwritten)
- Multiple benchmark runs accumulate in the same file
- Timestamps allow tracking performance over time
- CSV can be imported into spreadsheet tools for analysis

## Interpretation

### Understanding Results

**Execution Time:**
- Measures end-to-end task completion time
- Includes LLM inference, data processing, and I/O
- Lower is better
- Expected ranges (for qwen2.5:1.5b on typical hardware):
  - Roadmap: 25-40 seconds
  - Notes: 15-25 seconds
  - Quiz: 20-30 seconds
  - Evaluation: 40-50 seconds

**Peak RAM Usage:**
- Maximum memory consumed during task execution
- Includes Python process, model loading, and data structures
- Lower is better
- Expected range: 150-300 MB (depends on model size)

**Average CPU Usage:**
- Mean CPU utilization during task execution
- Higher values indicate CPU-bound operations (typical for LLM inference)
- Expected range: 60-90% (during active inference)

### Performance Trends

**Good Performance:**
- Consistent times across 3 runs (±10% variance)
- Stable memory usage
- No memory leaks (RAM returns to baseline)

**Potential Issues:**
- Increasing times across runs (may indicate memory pressure)
- Extremely high RAM usage (>500 MB)
- Very low CPU usage (<30%) during inference (may indicate I/O bottleneck)

### Comparing Results

To compare performance across changes:

1. Run benchmarks before changes (baseline)
2. Make your changes
3. Run benchmarks again
4. Compare average times and resource usage
5. Look for regressions (>10% increase in time/resources)

### Analysis Tips

```bash
# View all results
cat evaluation/results/performance_log.csv

# Count total runs
wc -l evaluation/results/performance_log.csv

# Filter by task
grep "roadmap_generation" evaluation/results/performance_log.csv

# Import into Python for analysis
import pandas as pd
df = pd.read_csv('evaluation/results/performance_log.csv')
print(df.groupby('task_name')['total_time_seconds'].describe())
```

## Limitations

### Known Constraints

1. **TTFT Approximation**
   - Time To First Token (TTFT) is approximated as total time
   - True TTFT requires streaming API support
   - Current implementation measures complete response time

2. **Single-Threaded Execution**
   - Benchmarks run sequentially, not concurrently
   - Does not test concurrent load handling
   - Real-world usage may involve parallel requests

3. **No Baseline Comparison**
   - Phase 1 only captures metrics
   - Does not automatically compare to historical baselines
   - Manual analysis required for trend detection

4. **Limited Scope**
   - Only measures computational performance
   - Does not measure quality metrics (accuracy, relevance)
   - Does not test error handling or edge cases

5. **Environment Dependency**
   - Results vary based on:
     - Hardware (CPU, RAM)
     - Operating system
     - Background processes
     - Model size and quantization
   - Not suitable for cross-machine comparison without normalization

6. **Test Data Simplicity**
   - Uses minimal test data to avoid cache pollution
   - May not reflect real-world content complexity
   - Performance may differ with larger/more complex inputs

7. **No Automated Regression Detection**
   - Does not automatically flag performance regressions
   - Requires manual review of results
   - No CI/CD integration in Phase 1

### Out of Scope (Phase 1)

The following features are not included in this initial implementation:

- Latency distribution analysis (P50, P95, P99)
- Concurrent load testing
- Memory leak detection over extended runs
- GPU utilization monitoring
- Automated regression detection
- Integration with CI/CD pipelines
- Quality benchmarking (accuracy, relevance)
- Comparison with historical baselines

These may be added in future phases based on requirements.

## Troubleshooting

### Common Issues

**Error: "Cannot import services"**
- Ensure you're running from project root directory
- Check that all dependencies are installed: `pip install -r requirements.txt`

**Error: "Ollama service is not available"**
- Start Ollama: `ollama serve`
- Verify model is available: `ollama list`
- Check Ollama URL in `.env` file

**Error: "Permission denied" on CSV file**
- Close any programs that have the CSV file open
- Check file permissions: `ls -l evaluation/results/`

**Benchmarks are very slow**
- Normal for CPU-only inference with small models
- Consider using GPU if available
- Reduce repetitions in `BENCHMARK_CONFIG` (not recommended)

**Results vary significantly between runs**
- Normal variance: ±10% is acceptable
- High variance (>20%) may indicate:
  - Background processes consuming resources
  - Thermal throttling
  - Memory pressure

### Getting Help

If you encounter issues:

1. Check that production system works normally
2. Verify Ollama is running and responsive
3. Review console output for specific error messages
4. Check `evaluation/results/performance_log.csv` for partial results
5. Ensure no production files were accidentally modified: `git status`

## Maintenance

### Cleaning Up Results

To start fresh:

```bash
# Remove old results (keeps directory structure)
rm evaluation/results/performance_log.csv

# Results will be recreated on next run
```

### Modifying Configuration

Edit `BENCHMARK_CONFIG` in `evaluation/benchmark_runner.py`:

```python
BENCHMARK_CONFIG = {
    'repetitions': 3,              # Number of runs per task
    'sampling_interval': 0.1,      # Resource sampling interval
    'csv_path': 'evaluation/results/performance_log.csv'
}
```

### Adding New Benchmarks

To benchmark additional tasks:

1. Create a new `benchmark_<task_name>()` function
2. Follow the existing pattern (monitor, time, execute, collect)
3. Add to the `tasks` list in `run_all_benchmarks()`
4. Update this README with the new task

## Summary

This benchmark harness provides a simple, isolated way to measure performance without touching production code. Use it to track trends, identify bottlenecks, and validate optimizations.

**Key Points:**
- ✅ No production code modified
- ✅ Complete isolation in `/evaluation` folder
- ✅ Automated execution with `python evaluation/benchmark_runner.py`
- ✅ CSV output for trend analysis
- ✅ Measures time, RAM, and CPU for 4 core tasks
- ✅ Reproducible results (±10% variance)

For questions or improvements, refer to the design document at `.kiro/specs/performance-benchmark-harness/design.md`.
