"""
Benchmark Runner for Performance Benchmarking

Orchestrates benchmark execution and coordinates monitoring.
"""

import sys
import time
import tempfile
import shutil
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Import error handling
try:
    from app.services.roadmap_service import RoadmapService
    from app.services.content_service import ContentService
    from app.services.quiz_service import QuizService
    from app.services.llm_service import LLMService
    from app.config import settings
    from app.models import LearningMode, Module
except ImportError as e:
    print(f"Error: Cannot import services. Ensure you're in project root.")
    print(f"Details: {e}")
    sys.exit(1)

try:
    from evaluation.system_monitor import SystemMonitor
    from evaluation.metrics_logger import log_result, ensure_results_directory
except ImportError as e:
    print(f"Error: Cannot import evaluation modules.")
    print(f"Details: {e}")
    sys.exit(1)


# Benchmark Configuration
BENCHMARK_CONFIG = {
    'repetitions': 3,
    'sampling_interval': 0.5,
    'csv_path': 'evaluation/results/performance_log.csv'
}


class CacheIsolation:
    """
    Context manager for isolated cache per task.
    Prevents production cache pollution.
    """
    
    def __init__(self):
        self.original_cache_dir = None
        self.temp_cache_dir = None
    
    def __enter__(self):
        # Save original cache directory
        self.original_cache_dir = settings.cache_dir
        
        # Create temporary cache directory
        self.temp_cache_dir = tempfile.mkdtemp(prefix="benchmark_cache_")
        
        # Override settings
        settings.cache_dir = self.temp_cache_dir
        
        return self.temp_cache_dir
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original cache directory
        settings.cache_dir = self.original_cache_dir
        
        # Clean up temp directory
        try:
            shutil.rmtree(self.temp_cache_dir, ignore_errors=True)
        except Exception as e:
            print(f"Warning: Failed to cleanup temp cache: {e}")


class LLMCallTracker:
    """
    Context manager to track LLM calls via monkey patching.
    Counts total LLM API calls during benchmark execution.
    """
    
    def __init__(self):
        self.call_count = 0
        self.original_method = None
    
    def __enter__(self):
        from app.services.llm_service import LLMService
        
        # Save original method
        self.original_method = LLMService._call_ollama
        
        # Create tracking wrapper
        tracker_self = self
        
        def tracked_call_ollama(llm_self, *args, **kwargs):
            tracker_self.call_count += 1
            return tracker_self.original_method(llm_self, *args, **kwargs)
        
        # Monkey patch
        LLMService._call_ollama = tracked_call_ollama
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        from app.services.llm_service import LLMService
        
        # Restore original method
        LLMService._call_ollama = self.original_method
        
        # Do NOT reset call_count - each instance manages its own count
    
    def get_call_count(self):
        return self.call_count


def get_model_name() -> str:
    """
    Read model name from settings.
    
    Returns:
        Model name as string for logging
    """
    return settings.ollama_model


def setup_test_environment() -> Dict[str, Any]:
    """
    Prepare test data for benchmarking.
    
    Returns:
        Dict with test input data
    """
    # Create minimal test input data
    test_data = {
        'input_text': """
        Introduction to DevOps
        
        DevOps is a set of practices that combines software development (Dev) and IT operations (Ops).
        It aims to shorten the systems development life cycle and provide continuous delivery with high software quality.
        
        Key Concepts:
        1. Continuous Integration (CI): Developers regularly merge code changes into a central repository
        2. Continuous Delivery (CD): Code changes are automatically built, tested, and prepared for release
        3. Infrastructure as Code: Managing infrastructure through code rather than manual processes
        4. Monitoring and Logging: Tracking application performance and user behavior
        
        Popular DevOps Tools:
        - Git: Version control system
        - Jenkins: Automation server for CI/CD
        - Docker: Containerization platform
        - Kubernetes: Container orchestration
        - Ansible: Configuration management
        
        Benefits of DevOps:
        - Faster deployment cycles
        - Improved collaboration between teams
        - Higher quality software
        - Better reliability and stability
        """,
        'mode': LearningMode.UNTIMED
    }
    
    return test_data


def benchmark_roadmap_generation(test_data: Dict[str, Any], run_number: int, run_type: str) -> Optional[Dict[str, Any]]:
    """
    Benchmark roadmap generation.
    
    Args:
        test_data: Test input data
        run_number: Current run number
        run_type: "cold" or "warm"
        
    Returns:
        Result dictionary with metrics, or None on failure
    """
    print(f"  Running roadmap generation (run {run_number}/3, {run_type})...")
    
    monitor = SystemMonitor()
    
    try:
        with LLMCallTracker() as llm_tracker:
            # Start monitoring
            monitor.start_monitoring()
            
            # Record start time
            start_time = time.perf_counter()
            
            # Execute task via service (created inside cache context)
            roadmap_service = RoadmapService()
            modules = roadmap_service.generate_roadmap(
                input_text=test_data['input_text'],
                mode=test_data['mode'],
                input_id='benchmark_test'
            )
            
            # Record end time
            end_time = time.perf_counter()
            
            # Stop monitoring and collect metrics
            metrics = monitor.stop_monitoring()
            
            # Get LLM call count
            llm_calls = llm_tracker.get_call_count()
            
            # Calculate total time
            total_time = end_time - start_time
            
            # Return result dict
            return {
                'task_name': 'roadmap_generation',
                'run_number': run_number,
                'run_type': run_type,
                'total_time_seconds': round(total_time, 2),
                'peak_ram_mb': metrics['peak_ram_mb'],
                'avg_cpu_percent': metrics['avg_cpu_percent'],
                'peak_cpu_percent': metrics['peak_cpu_percent'],
                'llm_call_count': llm_calls,
                'timestamp': datetime.now().isoformat(),
                'model_name': get_model_name()
            }
        
    except Exception as e:
        print(f"    Error: {str(e)}")
        traceback.print_exc()
        return None  # Skip logging on failure


def benchmark_notes_generation(test_data: Dict[str, Any], run_number: int, run_type: str) -> Optional[Dict[str, Any]]:
    """
    Benchmark notes generation for one module.
    
    Args:
        test_data: Test input data
        run_number: Current run number
        run_type: "cold" or "warm"
        
    Returns:
        Result dictionary with metrics, or None on failure
    """
    print(f"  Running notes generation (run {run_number}/3, {run_type})...")
    
    monitor = SystemMonitor()
    
    try:
        # Create a test module
        test_module = Module(
            module_id='mod_test123',
            topic_name='DevOps Fundamentals',
            estimated_hours=2,
            prerequisites=[],
            order=1
        )
        
        with LLMCallTracker() as llm_tracker:
            # Start monitoring
            monitor.start_monitoring()
            
            # Record start time
            start_time = time.perf_counter()
            
            # Execute task via service
            content_service = ContentService()
            notes = content_service.generate_notes(
                module=test_module,
                input_text=test_data['input_text']
            )
            
            # Record end time
            end_time = time.perf_counter()
            
            # Stop monitoring and collect metrics
            metrics = monitor.stop_monitoring()
            
            # Get LLM call count
            llm_calls = llm_tracker.get_call_count()
            
            # Calculate total time
            total_time = end_time - start_time
            
            # Return result dict
            return {
                'task_name': 'notes_generation',
                'run_number': run_number,
                'run_type': run_type,
                'total_time_seconds': round(total_time, 2),
                'peak_ram_mb': metrics['peak_ram_mb'],
                'avg_cpu_percent': metrics['avg_cpu_percent'],
                'peak_cpu_percent': metrics['peak_cpu_percent'],
                'llm_call_count': llm_calls,
                'timestamp': datetime.now().isoformat(),
                'model_name': get_model_name()
            }
        
    except Exception as e:
        print(f"    Error: {str(e)}")
        traceback.print_exc()
        return None  # Skip logging on failure


def benchmark_quiz_generation(test_data: Dict[str, Any], run_number: int, run_type: str) -> Optional[Dict[str, Any]]:
    """
    Benchmark quiz generation.
    
    Args:
        test_data: Test input data
        run_number: Current run number
        run_type: "cold" or "warm"
        
    Returns:
        Result dictionary with metrics, or None on failure
    """
    print(f"  Running quiz generation (run {run_number}/3, {run_type})...")
    
    monitor = SystemMonitor()
    
    try:
        # Create a test module
        test_module = Module(
            module_id='mod_test123',
            topic_name='DevOps Fundamentals',
            estimated_hours=2,
            prerequisites=[],
            order=1
        )
        
        with LLMCallTracker() as llm_tracker:
            # Start monitoring
            monitor.start_monitoring()
            
            # Record start time
            start_time = time.perf_counter()
            
            # Execute task via service
            quiz_service = QuizService()
            quiz = quiz_service.generate_quiz(
                module=test_module,
                content=test_data['input_text'],
                mode=test_data['mode']
            )
            
            # Record end time
            end_time = time.perf_counter()
            
            # Stop monitoring and collect metrics
            metrics = monitor.stop_monitoring()
            
            # Get LLM call count
            llm_calls = llm_tracker.get_call_count()
            
            # Calculate total time
            total_time = end_time - start_time
            
            # Return result dict
            return {
                'task_name': 'quiz_generation',
                'run_number': run_number,
                'run_type': run_type,
                'total_time_seconds': round(total_time, 2),
                'peak_ram_mb': metrics['peak_ram_mb'],
                'avg_cpu_percent': metrics['avg_cpu_percent'],
                'peak_cpu_percent': metrics['peak_cpu_percent'],
                'llm_call_count': llm_calls,
                'timestamp': datetime.now().isoformat(),
                'model_name': get_model_name()
            }
        
    except Exception as e:
        print(f"    Error: {str(e)}")
        traceback.print_exc()
        return None  # Skip logging on failure


def benchmark_quiz_evaluation(test_data: Dict[str, Any], run_number: int, run_type: str) -> Optional[Dict[str, Any]]:
    """
    Benchmark quiz evaluation (first attempt only).
    
    Args:
        test_data: Test input data
        run_number: Current run number
        run_type: "cold" or "warm"
        
    Returns:
        Result dictionary with metrics, or None on failure
    """
    print(f"  Running quiz evaluation (run {run_number}/3, {run_type})...")
    
    monitor = SystemMonitor()
    
    try:
        # Create a test module and quiz first
        test_module = Module(
            module_id='mod_test123',
            topic_name='DevOps Fundamentals',
            estimated_hours=2,
            prerequisites=[],
            order=1
        )
        
        quiz_service = QuizService()
        
        # Cache the roadmap (required for evaluation to find module info)
        roadmap_data = {
            "modules": [test_module.model_dump()]
        }
        quiz_service.cache_service.cache_roadmap(roadmap_data)
        
        quiz = quiz_service.generate_quiz(
            module=test_module,
            content=test_data['input_text'],
            mode=test_data['mode']
        )
        
        # Cache the quiz (required for evaluation to work)
        quiz_qa_data = {
            "quiz_id": quiz.quiz_id,
            "module_id": quiz.module_id,
            "questions": [q.model_dump() for q in quiz.questions],
            "mode": quiz.mode.value,
            "time_limit_seconds": quiz.time_limit_seconds,
            "created_at": quiz.created_at.isoformat()
        }
        quiz_service.cache_service.cache_quiz_qa(quiz.module_id, quiz_qa_data)
        
        # Create dummy user answers
        user_answers = {i: quiz.questions[i-1].options[0] for i in range(1, 6)}
        
        # Submit quiz
        submission_id = quiz_service.submit_quiz_submission(
            quiz_id=quiz.quiz_id,
            module_id=test_module.module_id,
            user_answers=user_answers,
            time_taken_seconds=60,
            attempt_number=1
        )
        
        with LLMCallTracker() as llm_tracker:
            # Start monitoring
            monitor.start_monitoring()
            
            # Record start time
            start_time = time.perf_counter()
            
            # Execute evaluation
            evaluation = quiz_service.evaluate_quiz_submission(
                quiz_id=quiz.quiz_id,
                module_id=test_module.module_id,
                content=test_data['input_text'],
                attempt_number=1
            )
            
            # Record end time
            end_time = time.perf_counter()
            
            # Stop monitoring and collect metrics
            metrics = monitor.stop_monitoring()
            
            # Get LLM call count
            llm_calls = llm_tracker.get_call_count()
            
            # Calculate total time
            total_time = end_time - start_time
            
            # Return result dict
            return {
                'task_name': 'quiz_evaluation',
                'run_number': run_number,
                'run_type': run_type,
                'total_time_seconds': round(total_time, 2),
                'peak_ram_mb': metrics['peak_ram_mb'],
                'avg_cpu_percent': metrics['avg_cpu_percent'],
                'peak_cpu_percent': metrics['peak_cpu_percent'],
                'llm_call_count': llm_calls,
                'timestamp': datetime.now().isoformat(),
                'model_name': get_model_name()
            }
        
    except Exception as e:
        print(f"    Error: {str(e)}")
        traceback.print_exc()
        return None  # Skip logging on failure


def run_all_benchmarks() -> List[Dict[str, Any]]:
    """
    Execute all benchmarks with cold/warm runs.
    
    Cold run = fresh temp cache
    Warm runs = reuse same temp cache
    
    Returns:
        List of all benchmark results
    """
    results = []
    
    # Setup test environment
    test_data = setup_test_environment()
    
    # Define benchmark tasks
    tasks = [
        ('Roadmap Generation', benchmark_roadmap_generation),
        ('Notes Generation', benchmark_notes_generation),
        ('Quiz Generation', benchmark_quiz_generation),
        ('Quiz Evaluation', benchmark_quiz_evaluation)
    ]
    
    # Execute each task with cold/warm runs
    for task_name, benchmark_func in tasks:
        print(f"\n{task_name}:")
        
        # Run 1: COLD - fresh temp cache
        with CacheIsolation() as temp_cache_cold:
            try:
                result = benchmark_func(test_data, 1, "cold")
                if result:  # Only log if not None
                    results.append(result)
                    log_result(result, BENCHMARK_CONFIG['csv_path'])
                    print(f"    Completed: {result['total_time_seconds']}s (cold, {result['llm_call_count']} LLM calls)")
            except Exception as e:
                print(f"    Failed: {str(e)}")
                continue
        
        # Runs 2-3: WARM - reuse same temp cache
        with CacheIsolation() as temp_cache_warm:
            for run_num in [2, 3]:
                try:
                    result = benchmark_func(test_data, run_num, "warm")
                    if result:  # Only log if not None
                        results.append(result)
                        log_result(result, BENCHMARK_CONFIG['csv_path'])
                        print(f"    Completed: {result['total_time_seconds']}s (warm, {result['llm_call_count']} LLM calls)")
                except Exception as e:
                    print(f"    Failed: {str(e)}")
                    continue
    
    return results


def compute_averages(results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Group results by task_name and calculate averages.
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Summary dict with averages per task
    """
    # Group by task_name
    grouped = {}
    for result in results:
        task_name = result['task_name']
        if task_name not in grouped:
            grouped[task_name] = []
        grouped[task_name].append(result)
    
    # Calculate averages
    summary = {}
    for task_name, task_results in grouped.items():
        if not task_results:
            continue
            
        avg_time = sum(r['total_time_seconds'] for r in task_results) / len(task_results)
        avg_ram = sum(r['peak_ram_mb'] for r in task_results) / len(task_results)
        avg_cpu = sum(r['avg_cpu_percent'] for r in task_results) / len(task_results)
        
        summary[task_name] = {
            'avg_time': round(avg_time, 2),
            'avg_ram': round(avg_ram, 2),
            'avg_cpu': round(avg_cpu, 2)
        }
    
    return summary


def print_summary(results: List[Dict[str, Any]]):
    """
    Print formatted summary to console.
    
    Args:
        results: List of all benchmark results
    """
    if not results:
        print("\nNo results to summarize.")
        return
    
    print("\n" + "="*80)
    print("BENCHMARK SUMMARY")
    print("="*80)
    
    # Compute averages
    summary = compute_averages(results)
    
    # Print table header
    print(f"\n{'Task':<25} {'Avg Time (s)':<15} {'Avg RAM (MB)':<15} {'Avg CPU (%)':<15}")
    print("-"*80)
    
    # Print each task
    for task_name, metrics in summary.items():
        display_name = task_name.replace('_', ' ').title()
        print(f"{display_name:<25} {metrics['avg_time']:<15} {metrics['avg_ram']:<15} {metrics['avg_cpu']:<15}")
    
    # Print overall stats
    print("\n" + "-"*80)
    peak_ram = max(r['peak_ram_mb'] for r in results)
    peak_cpu = max(r['avg_cpu_percent'] for r in results)
    total_time = sum(r['total_time_seconds'] for r in results)
    
    print(f"Peak RAM Usage: {peak_ram:.2f} MB")
    print(f"Peak CPU Usage: {peak_cpu:.2f}%")
    print(f"Total Benchmark Duration: {total_time:.2f}s ({total_time/60:.1f} minutes)")
    print(f"Model: {get_model_name()}")
    print("="*80)


def main():
    """
    Entry point for benchmark execution.
    """
    # Print banner
    print("\n" + "="*80)
    print("COGNITIVE AI LEARNING PLATFORM - PERFORMANCE BENCHMARK")
    print("="*80)
    print(f"Model: {get_model_name()}")
    print(f"Repetitions per task: {BENCHMARK_CONFIG['repetitions']}")
    print(f"Results will be saved to: {BENCHMARK_CONFIG['csv_path']}")
    print("="*80)
    
    try:
        # Ensure results directory exists
        ensure_results_directory()
        
        # Run all benchmarks
        print("\nStarting benchmarks...")
        results = run_all_benchmarks()
        
        # Print summary
        print_summary(results)
        
        # Print completion message
        print(f"\n✓ Benchmarks complete! Results saved to {BENCHMARK_CONFIG['csv_path']}")
        print("\n")
        
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
