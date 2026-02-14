# Phase 2 Quality Improvements - Summary

## Problem Identified
Initial implementation had unrealistic metrics:
- RAM: 30-65 MB (too low for LLM inference)
- CPU: 0.3-9% average (too low for computation)

**Root Cause**: Monitoring only Python process, not Ollama server where LLM runs.

## Solution Implemented

### System-Wide Monitoring
Changed from process-specific to system-wide resource monitoring:

**Before**:
```python
self.process = psutil.Process()  # Only Python process
cpu = self.process.cpu_percent()  # Python CPU only
ram = self.process.memory_info().rss  # Python RAM only
```

**After**:
```python
mem = psutil.virtual_memory()  # System-wide memory
cpu = psutil.cpu_percent()  # System-wide CPU
ram_delta = current_ram - baseline_ram  # RAM increase during benchmark
```

### Key Changes

1. **RAM Measurement**: System-wide memory delta (increase from baseline)
2. **CPU Measurement**: System-wide CPU usage (all cores combined)
3. **Baseline Tracking**: Record baseline before benchmark, report delta
4. **Captures Ollama**: Now includes LLM server resource usage

## Results Comparison

### Before (Process-Only)
- RAM: 30-65 MB
- CPU Avg: 3-9%
- CPU Peak: 66-111%

### After (System-Wide)
- RAM: 0-808 MB (realistic for LLM)
- CPU Avg: 14-38% (realistic for inference)
- CPU Peak: 22-68% (realistic spikes)

## Validation

✅ Cold run RAM (808 MB) matches model loading + inference
✅ Warm run RAM (0-104 MB) shows cached model
✅ CPU usage realistic for LLM inference workload
✅ LLM retry tracking works (quiz gen run 3: 2 calls)

## Conclusion

System-wide monitoring provides accurate resource metrics that capture the full cost of LLM inference, including external processes like Ollama server.
