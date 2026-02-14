"""
Visualization Generator for Performance Benchmark Results

Generates comparison graphs from existing CSV files.
Does NOT rerun benchmarks or modify any production code.
"""

import sys
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style for clean visualizations
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['font.size'] = 10


def ensure_output_directory():
    """Create visualizations directory if it doesn't exist."""
    output_dir = Path("evaluation/visualizations")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def load_comparison_results():
    """Load model comparison results from CSV."""
    csv_path = "evaluation/model_comparison/comparison_results.csv"
    try:
        df = pd.read_csv(csv_path)
        print(f"✓ Loaded {len(df)} models from {csv_path}")
        return df
    except Exception as e:
        print(f"Error loading {csv_path}: {e}")
        sys.exit(1)


def generate_cold_latency_chart(df, output_dir):
    """
    Graph 1: Cold Start Latency Comparison
    Bar chart showing cold start times for each model.
    """
    print("\n[1/5] Generating cold latency chart...")
    
    plt.figure(figsize=(10, 6))
    
    # Create bar chart
    bars = plt.bar(df['model_name'], df['cold_time_seconds'], 
                   color=['#3498db', '#e74c3c', '#2ecc71'])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}s',
                ha='center', va='bottom', fontsize=10)
    
    plt.title('Cold Start Latency Comparison', fontsize=14, fontweight='bold')
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Cold Start Time (seconds)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    output_path = output_dir / "cold_latency.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Saved: {output_path}")


def generate_warm_latency_chart(df, output_dir):
    """
    Graph 2: Warm Latency Comparison
    Bar chart showing warm run times for each model.
    """
    print("\n[2/5] Generating warm latency chart...")
    
    plt.figure(figsize=(10, 6))
    
    # Create bar chart
    bars = plt.bar(df['model_name'], df['warm_time_seconds'],
                   color=['#9b59b6', '#f39c12', '#1abc9c'])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}s',
                ha='center', va='bottom', fontsize=10)
    
    plt.title('Warm Run Latency Comparison', fontsize=14, fontweight='bold')
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Warm Run Time (seconds)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    output_path = output_dir / "warm_latency.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Saved: {output_path}")


def generate_peak_ram_chart(df, output_dir):
    """
    Graph 3: Peak RAM Usage Comparison
    Bar chart showing peak RAM usage for each model.
    """
    print("\n[3/5] Generating peak RAM usage chart...")
    
    plt.figure(figsize=(10, 6))
    
    # Create bar chart
    bars = plt.bar(df['model_name'], df['peak_ram_mb'],
                   color=['#e67e22', '#16a085', '#c0392b'])
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.0f} MB',
                ha='center', va='bottom', fontsize=10)
    
    plt.title('Peak RAM Usage Comparison', fontsize=14, fontweight='bold')
    plt.xlabel('Model', fontsize=12)
    plt.ylabel('Peak RAM Usage (MB)', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    output_path = output_dir / "peak_ram_usage.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Saved: {output_path}")


def generate_accuracy_comparison_chart(df, output_dir):
    """
    Graph 4: Accuracy Comparison (Grouped Bar Chart)
    Shows syllabus, concept, and JSON compliance metrics side by side.
    """
    print("\n[4/5] Generating accuracy comparison chart...")
    
    # Prepare data for grouped bar chart
    metrics = ['syllabus_adherence_percent', 'concept_accuracy_percent', 
               'json_compliance_percent']
    metric_labels = ['Syllabus Adherence', 'Concept Accuracy', 'JSON Compliance']
    
    x = range(len(df))
    width = 0.25
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Create grouped bars
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        offset = width * (i - 1)
        bars = ax.bar([p + offset for p in x], df[metric], width, label=label)
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}%',
                   ha='center', va='bottom', fontsize=9)
    
    ax.set_title('Model Accuracy Comparison', fontsize=14, fontweight='bold')
    ax.set_xlabel('Model', fontsize=12)
    ax.set_ylabel('Accuracy (%)', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(df['model_name'], rotation=45, ha='right')
    ax.legend(loc='upper right')
    ax.set_ylim(0, 110)  # Give space for labels
    
    plt.tight_layout()
    
    output_path = output_dir / "accuracy_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Saved: {output_path}")


def generate_performance_tradeoff_chart(df, output_dir):
    """
    Graph 5: Performance vs Accuracy Tradeoff (Scatter Plot)
    X-axis: RAM usage, Y-axis: Accuracy, Size: Cold start time
    """
    print("\n[5/5] Generating performance tradeoff chart...")
    
    plt.figure(figsize=(10, 8))
    
    # Create scatter plot with size proportional to cold time
    sizes = df['cold_time_seconds'] * 50  # Scale for visibility
    
    scatter = plt.scatter(df['peak_ram_mb'], df['syllabus_adherence_percent'],
                         s=sizes, alpha=0.6, c=range(len(df)), cmap='viridis',
                         edgecolors='black', linewidth=1.5)
    
    # Add model name labels
    for idx, row in df.iterrows():
        plt.annotate(row['model_name'],
                    (row['peak_ram_mb'], row['syllabus_adherence_percent']),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    
    plt.title('Performance vs Accuracy Tradeoff\n(Bubble size = Cold start time)',
             fontsize=14, fontweight='bold')
    plt.xlabel('Peak RAM Usage (MB)', fontsize=12)
    plt.ylabel('Syllabus Adherence (%)', fontsize=12)
    plt.grid(True, alpha=0.3)
    
    # Add legend for bubble sizes
    legend_sizes = [df['cold_time_seconds'].min(), 
                   df['cold_time_seconds'].median(),
                   df['cold_time_seconds'].max()]
    legend_labels = [f'{s:.1f}s' for s in legend_sizes]
    legend_handles = [plt.scatter([], [], s=s*50, c='gray', alpha=0.6, edgecolors='black')
                     for s in legend_sizes]
    plt.legend(legend_handles, legend_labels, title='Cold Start Time',
              loc='lower right', frameon=True, fontsize=10)
    
    plt.tight_layout()
    
    output_path = output_dir / "performance_tradeoff.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Saved: {output_path}")


def main():
    """Main entry point for graph generation."""
    print("\n" + "="*80)
    print("PERFORMANCE BENCHMARK VISUALIZATION GENERATOR")
    print("="*80)
    print("\nGenerating graphs from existing CSV files...")
    print("(No benchmarks will be rerun)")
    
    # Ensure output directory exists
    output_dir = ensure_output_directory()
    print(f"\n✓ Output directory: {output_dir}")
    
    # Load comparison results
    df = load_comparison_results()
    
    # Generate all graphs
    generate_cold_latency_chart(df, output_dir)
    generate_warm_latency_chart(df, output_dir)
    generate_peak_ram_chart(df, output_dir)
    generate_accuracy_comparison_chart(df, output_dir)
    generate_performance_tradeoff_chart(df, output_dir)
    
    # Summary
    print("\n" + "="*80)
    print("VISUALIZATION COMPLETE")
    print("="*80)
    print(f"\nGenerated 5 graphs in: {output_dir}")
    print("\nFiles created:")
    print("  1. cold_latency.png")
    print("  2. warm_latency.png")
    print("  3. peak_ram_usage.png")
    print("  4. accuracy_comparison.png")
    print("  5. performance_tradeoff.png")
    print("\n✓ All visualizations generated successfully!\n")


if __name__ == "__main__":
    main()
