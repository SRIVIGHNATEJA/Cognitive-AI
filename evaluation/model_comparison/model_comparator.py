"""
Model Comparison Module

Compares multiple LLM models on performance and accuracy metrics.
Reuses existing benchmark and golden test logic without duplication.
"""

import sys
import csv
import time
import httpx
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from app.config import settings
    from app.models import LearningMode
except ImportError as e:
    print(f"Error: Cannot import app modules. Ensure you're in project root.")
    print(f"Details: {e}")
    sys.exit(1)

try:
    from evaluation.benchmark_runner import (
        benchmark_roadmap_generation,
        setup_test_environment,
        CacheIsolation
    )
    from evaluation.golden_tests.golden_test_runner import GoldenTestRunner
except ImportError as e:
    print(f"Error: Cannot import evaluation modules.")
    print(f"Details: {e}")
    sys.exit(1)


class ModelComparator:
    """
    Orchestrates model comparison by reusing existing benchmark and test logic.
    """
    
    def __init__(self, output_path: str = "evaluation/model_comparison/comparison_results.csv"):
        self.output_path = output_path
        self.original_model_name = settings.ollama_model
        self.results = []
    
    def unload_ollama_model(self):
        """
        Unload current model from Ollama to free memory.
        This ensures accurate RAM measurements for the next model.
        """
        try:
            print(f"    Unloading previous model from memory...")
            
            # Call Ollama API to unload model
            # Using keep_alive=0 tells Ollama to immediately unload
            url = f"{settings.ollama_base_url}/api/generate"
            payload = {
                "model": settings.ollama_model,
                "prompt": "",
                "keep_alive": 0  # Unload immediately
            }
            
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
            
            # Wait for memory to stabilize
            time.sleep(3)
            
            print(f"    ✓ Model unloaded")
            
        except Exception as e:
            print(f"    Warning: Failed to unload model: {e}")
            # Continue anyway - not critical
    
    def run_performance_subset(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Run performance benchmark subset for one model.
        
        Only runs roadmap_generation benchmark (1 cold + 1 warm run).
        
        Args:
            model_name: Model to test
            
        Returns:
            Dict with performance metrics, or None on failure
        """
        print(f"\n  Running performance benchmark for {model_name}...")
        
        try:
            # Override model name
            settings.ollama_model = model_name
            
            # Setup test data
            test_data = setup_test_environment()
            
            # Run cold benchmark
            print(f"    Cold run...")
            with CacheIsolation():
                cold_result = benchmark_roadmap_generation(test_data, 1, "cold")
            
            if not cold_result:
                print(f"    Cold run failed")
                return None
            
            # Run warm benchmark
            print(f"    Warm run...")
            with CacheIsolation() as temp_cache:
                # First run to populate cache
                benchmark_roadmap_generation(test_data, 1, "cold")
                # Second run with warm cache
                warm_result = benchmark_roadmap_generation(test_data, 2, "warm")
            
            if not warm_result:
                print(f"    Warm run failed")
                return None
            
            # Extract metrics
            metrics = {
                'cold_time_seconds': cold_result['total_time_seconds'],
                'warm_time_seconds': warm_result['total_time_seconds'],
                'peak_ram_mb': max(cold_result['peak_ram_mb'], warm_result['peak_ram_mb'])
            }
            
            print(f"    ✓ Cold: {metrics['cold_time_seconds']}s, "
                  f"Warm: {metrics['warm_time_seconds']}s, "
                  f"RAM: {metrics['peak_ram_mb']}MB")
            
            return metrics
            
        except Exception as e:
            print(f"    Error: {str(e)}")
            return None
        
        finally:
            # Restore original model name
            settings.ollama_model = self.original_model_name
    
    def run_accuracy_tests(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Run golden set accuracy tests for one model.
        
        Args:
            model_name: Model to test
            
        Returns:
            Dict with accuracy metrics, or None on failure
        """
        print(f"\n  Running accuracy tests for {model_name}...")
        
        try:
            # Override model name
            settings.ollama_model = model_name
            
            # Create golden test runner
            runner = GoldenTestRunner()
            
            # Load golden set
            runner.load_golden_set()
            
            # Run all tests (suppresses output)
            summary = runner.run_all_tests()
            
            # Extract metrics
            metrics = {
                'syllabus_adherence_percent': round(summary['syllabus_adherence'], 1),
                'concept_accuracy_percent': round(summary['concept_accuracy'], 1),
                'hallucination_pass_percent': round(summary['hallucination_pass_rate'], 1),
                'json_compliance_percent': round(summary['json_compliance_rate'], 1)
            }
            
            print(f"    ✓ Syllabus: {metrics['syllabus_adherence_percent']}%, "
                  f"Concept: {metrics['concept_accuracy_percent']}%, "
                  f"Hallucination: {metrics['hallucination_pass_percent']}%, "
                  f"JSON: {metrics['json_compliance_percent']}%")
            
            return metrics
            
        except Exception as e:
            print(f"    Error: {str(e)}")
            return None
        
        finally:
            # Restore original model name
            settings.ollama_model = self.original_model_name
    
    def compare_models(self, model_list: List[str]):
        """
        Compare multiple models on performance and accuracy.
        
        Args:
            model_list: List of model names to compare
        """
        print("\n" + "="*80)
        print("MODEL COMPARISON")
        print("="*80)
        print(f"Models to compare: {', '.join(model_list)}")
        print(f"Hardware: 8GB Mac M3")
        print("="*80)
        
        for model_name in model_list:
            print(f"\n[{model_list.index(model_name) + 1}/{len(model_list)}] Testing: {model_name}")
            print("-" * 80)
            
            # Unload previous model to ensure clean memory baseline
            if model_list.index(model_name) > 0:
                self.unload_ollama_model()
            
            # Run performance subset
            perf_metrics = self.run_performance_subset(model_name)
            
            if not perf_metrics:
                print(f"  ✗ Performance benchmark failed for {model_name}")
                continue
            
            # Run accuracy tests
            accuracy_metrics = self.run_accuracy_tests(model_name)
            
            if not accuracy_metrics:
                print(f"  ✗ Accuracy tests failed for {model_name}")
                continue
            
            # Combine metrics
            result = {
                'model_name': model_name,
                **perf_metrics,
                **accuracy_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
            self.results.append(result)
            
            # Save incrementally
            self.save_result(result)
            
            print(f"  ✓ {model_name} complete")
        
        # Print summary table
        self.print_summary()
    
    def save_result(self, result: Dict[str, Any]):
        """
        Save single result to CSV (append mode).
        
        Args:
            result: Result dictionary to save
        """
        try:
            # Ensure directory exists
            Path(self.output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists
            file_exists = Path(self.output_path).exists()
            
            # Define fieldnames
            fieldnames = [
                'model_name',
                'cold_time_seconds',
                'warm_time_seconds',
                'peak_ram_mb',
                'syllabus_adherence_percent',
                'concept_accuracy_percent',
                'hallucination_pass_percent',
                'json_compliance_percent',
                'timestamp'
            ]
            
            # Write to CSV
            with open(self.output_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if new file
                if not file_exists:
                    writer.writeheader()
                
                # Write result
                writer.writerow(result)
            
        except Exception as e:
            print(f"  Warning: Failed to save result: {e}")
    
    def print_summary(self):
        """Print formatted comparison summary table."""
        if not self.results:
            print("\nNo results to display.")
            return
        
        print("\n" + "="*80)
        print("COMPARISON SUMMARY")
        print("="*80)
        
        # Print table header
        print(f"\n{'Model':<20} {'Cold (s)':<10} {'Warm (s)':<10} {'RAM (MB)':<10} "
              f"{'Syllabus':<10} {'Concept':<10} {'Halluc':<10} {'JSON':<10}")
        print("-" * 80)
        
        # Print each model
        for result in self.results:
            print(f"{result['model_name']:<20} "
                  f"{result['cold_time_seconds']:<10} "
                  f"{result['warm_time_seconds']:<10} "
                  f"{result['peak_ram_mb']:<10} "
                  f"{result['syllabus_adherence_percent']:<10} "
                  f"{result['concept_accuracy_percent']:<10} "
                  f"{result['hallucination_pass_percent']:<10} "
                  f"{result['json_compliance_percent']:<10}")
        
        print("\n" + "="*80)
        print(f"Results saved to: {self.output_path}")
        print("="*80)


def main():
    """Main entry point for model comparison."""
    
    # Define models to compare
    # User should modify this list based on available models
    models_to_compare = [
        "qwen2.5:1.5b",
        "llama3.2:1b",
        "phi:2.7b",
    ]
    
    print("\n" + "="*80)
    print("COGNITIVE AI LEARNING PLATFORM - MODEL COMPARISON")
    print("="*80)
    print("\nIMPORTANT: Ensure all models are pulled before running:")
    for model in models_to_compare:
        print(f"  ollama pull {model}")
    print("\nPress Ctrl+C to cancel, or wait 5 seconds to continue...")
    print("="*80)
    
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(0)
    
    # Create comparator
    comparator = ModelComparator()
    
    # Run comparison
    try:
        comparator.compare_models(models_to_compare)
        print("\n✓ Model comparison complete!\n")
    except KeyboardInterrupt:
        print("\n\nComparison interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
