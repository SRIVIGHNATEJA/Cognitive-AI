"""
Metrics Logger for Performance Benchmarking

Logs benchmark results to CSV file.
"""

import os
import csv


def ensure_results_directory():
    """
    Check if evaluation/results/ exists.
    Create if missing using os.makedirs(exist_ok=True).
    """
    try:
        results_dir = "evaluation/results"
        os.makedirs(results_dir, exist_ok=True)
    except Exception as e:
        raise RuntimeError(f"Failed to create results directory: {e}")


def initialize_csv_if_needed(csv_path: str = "evaluation/results/performance_log.csv"):
    """
    Check if CSV file exists.
    If not, create with headers.
    
    Headers: task_name, run_number, run_type, total_time_seconds, peak_ram_mb, 
             avg_cpu_percent, peak_cpu_percent, llm_call_count, timestamp, model_name
    """
    try:
        if not os.path.exists(csv_path):
            # Ensure directory exists
            ensure_results_directory()
            
            # Create CSV with headers
            headers = [
                'task_name',
                'run_number',
                'run_type',
                'total_time_seconds',
                'peak_ram_mb',
                'avg_cpu_percent',
                'peak_cpu_percent',
                'llm_call_count',
                'timestamp',
                'model_name'
            ]
            
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                
    except Exception as e:
        raise RuntimeError(f"Failed to initialize CSV file: {e}")


def log_result(result: dict, csv_path: str = "evaluation/results/performance_log.csv"):
    """
    Append single benchmark result to CSV.
    
    Args:
        result: Dict with keys matching CSV columns
        csv_path: Path to CSV file
    """
    try:
        # Ensure CSV exists with headers
        initialize_csv_if_needed(csv_path)
        
        # Define fieldnames
        fieldnames = [
            'task_name',
            'run_number',
            'run_type',
            'total_time_seconds',
            'peak_ram_mb',
            'avg_cpu_percent',
            'peak_cpu_percent',
            'llm_call_count',
            'timestamp',
            'model_name'
        ]
        
        # Open CSV in append mode
        with open(csv_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(result)
            # Flush after write
            f.flush()
            
    except Exception as e:
        raise RuntimeError(f"Failed to log result to CSV: {e}")


def log_batch_results(results: list, csv_path: str = "evaluation/results/performance_log.csv"):
    """
    Append multiple benchmark results to CSV.
    
    Args:
        results: List of result dicts
        csv_path: Path to CSV file
    """
    try:
        # Call log_result() for each result in batch
        for result in results:
            log_result(result, csv_path)
            
    except Exception as e:
        raise RuntimeError(f"Failed to log batch results: {e}")
