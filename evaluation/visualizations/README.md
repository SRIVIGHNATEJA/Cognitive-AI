# Performance Benchmark Visualizations

## Overview

This directory contains visual representations of the performance benchmark results. All graphs are generated from existing CSV files without rerunning any benchmarks.

## Generated Graphs

### 1. Cold Start Latency Comparison (`cold_latency.png`)
**Type**: Bar Chart  
**Data Source**: `evaluation/model_comparison/comparison_results.csv`  
**Metrics**: Cold start time (seconds) for each model  

**Key Insights**:
- qwen2.5:1.5b: Fastest cold start (8.78s)
- llama3.2:1b: Moderate cold start (11.67s)
- phi:2.7b: Slowest cold start (15.87s)

### 2. Warm Run Latency Comparison (`warm_latency.png`)
**Type**: Bar Chart  
**Data Source**: `evaluation/model_comparison/comparison_results.csv`  
**Metrics**: Warm run time (seconds) for each model  

**Key Insights**:
- phi:2.7b: Exceptional warm performance (2.01s) - Best cache utilization!
- qwen2.5:1.5b: Good warm performance (6.58s)
- llama3.2:1b: Moderate warm performance (8.24s)

### 3. Peak RAM Usage Comparison (`peak_ram_usage.png`)
**Type**: Bar Chart  
**Data Source**: `evaluation/model_comparison/comparison_results.csv`  
**Metrics**: Peak RAM usage (MB) for each model  

**Key Insights**:
- llama3.2:1b: Most memory efficient (537.55 MB)
- qwen2.5:1.5b: Moderate memory usage (865.36 MB)
- phi:2.7b: Highest memory usage (1457.14 MB)

### 4. Accuracy Comparison (`accuracy_comparison.png`)
**Type**: Grouped Bar Chart  
**Data Source**: `evaluation/model_comparison/comparison_results.csv`  
**Metrics**: 
- Syllabus Adherence (%)
- Concept Accuracy (%)
- JSON Compliance (%)

**Key Insights**:
- qwen2.5:1.5b: Best overall accuracy (92% syllabus, 100% JSON)
- llama3.2:1b: Best concept accuracy (80%), good syllabus (88%)
- phi:2.7b: Good syllabus (88%), moderate concept (60%)
- All models: 100% hallucination resistance

### 5. Performance vs Accuracy Tradeoff (`performance_tradeoff.png`)
**Type**: Scatter Plot  
**Data Source**: `evaluation/model_comparison/comparison_results.csv`  
**Axes**: 
- X-axis: Peak RAM Usage (MB)
- Y-axis: Syllabus Adherence (%)
- Bubble size: Cold start time (seconds)

**Key Insights**:
- Shows the tradeoff between memory usage and accuracy
- Larger models (phi:2.7b) use more RAM but have slower cold starts
- Smaller models (llama3.2:1b) are memory efficient but may sacrifice some accuracy
- qwen2.5:1.5b offers best balance of accuracy and performance

## Usage

### Generate All Graphs

```bash
PYTHONPATH=. python evaluation/visualizations/generate_graphs.py
```

### Requirements

The visualization script requires:
- pandas >= 2.0.0
- matplotlib >= 3.7.0
- seaborn >= 0.12.0

These are included in `requirements.txt`.

### Output

All graphs are saved as high-resolution PNG files (300 DPI) in this directory.

## Design Decisions

### Color Schemes
- Each graph uses distinct colors for visual clarity
- Grouped bar charts use consistent colors across metrics
- Scatter plot uses viridis colormap for gradient effect

### Layout
- All graphs use tight layout to maximize space utilization
- Value labels are added directly on bars for easy reading
- Titles are bold and descriptive
- Axis labels are clear and include units

### Resolution
- All graphs are saved at 300 DPI for publication quality
- PNG format for universal compatibility

## Data Sources

### Model Comparison Results
**File**: `evaluation/model_comparison/comparison_results.csv`  
**Contains**:
- model_name
- cold_time_seconds
- warm_time_seconds
- peak_ram_mb
- syllabus_adherence_percent
- concept_accuracy_percent
- hallucination_pass_percent
- json_compliance_percent
- timestamp

### Performance Log (Not currently visualized)
**File**: `evaluation/results/performance_log.csv`  
**Contains**: Detailed per-task performance metrics

### Golden Test Results (Not currently visualized)
**File**: `evaluation/results/golden_results.csv`  
**Contains**: Detailed per-test accuracy results

## Interpretation Guide

### Cold vs Warm Latency
- **Cold start**: First run with fresh cache (model loading + inference)
- **Warm run**: Subsequent run with populated cache (inference only)
- Large difference indicates good cache utilization

### RAM Usage
- Measured as peak increase from baseline during benchmark
- Includes model loading and inference overhead
- Critical for deployment on memory-constrained hardware (8GB Mac M3)

### Accuracy Metrics
- **Syllabus Adherence**: Coverage of expected topics in roadmap generation
- **Concept Accuracy**: Presence of expected concepts, absence of forbidden ones
- **JSON Compliance**: Structural correctness of generated quizzes
- **Hallucination Resistance**: Avoidance of fabricated information (all models: 100%)

### Performance Tradeoff
- Top-right quadrant: High accuracy, high memory (phi:2.7b)
- Bottom-left quadrant: Lower accuracy, low memory (llama3.2:1b)
- Sweet spot: Balance of both (qwen2.5:1.5b)

## Recommendations Based on Visualizations

### For 8GB RAM Constraints
**Choose**: llama3.2:1b
- Lowest memory footprint (537 MB)
- Good accuracy (88% syllabus, 80% concept)
- Reasonable performance

### For Highest Accuracy
**Choose**: qwen2.5:1.5b
- Best syllabus adherence (92%)
- Perfect JSON compliance (100%)
- Fastest cold start (8.78s)

### For Cached/Repeated Workloads
**Choose**: phi:2.7b
- Exceptional warm run performance (2.01s)
- Good accuracy (88% syllabus)
- Requires more RAM (1457 MB)

## Future Enhancements

Potential additional visualizations:
- Time series graphs showing performance over multiple runs
- Heatmap of accuracy metrics across all test cases
- Box plots showing variance in performance
- Cost analysis (inference time × compute cost)
- Comparison with industry benchmarks

## Notes

- All visualizations are generated from existing CSV files
- No benchmarks are rerun during visualization generation
- Production code (benchmark_runner.py, golden_test_runner.py, model_comparator.py) remains unchanged
- Graphs can be regenerated at any time without affecting benchmark data
