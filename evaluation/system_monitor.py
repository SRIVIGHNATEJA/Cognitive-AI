"""
System Monitor for Performance Benchmarking

Monitors system-wide RAM and CPU usage during benchmark execution.
Captures resource usage from all processes including Ollama server.
"""

import psutil
import threading
import time


class SystemMonitor:
    """
    Monitors system-wide RAM and CPU usage during benchmark execution.
    
    Measures total system resources to capture LLM inference overhead
    from external processes like Ollama server.
    """
    
    def __init__(self):
        """Initialize monitor with baseline metrics."""
        self.baseline_ram_mb = None
        self.baseline_ram_percent = None
        self.peak_ram_mb = None
        self.peak_ram_percent = None
        self.cpu_samples = []
        self.ram_samples = []
        self.monitoring = False
        self._monitor_thread = None
    
    def start_monitoring(self):
        """
        Start monitoring system-wide resources.
        Records baseline RAM and CPU usage.
        Starts sampling thread.
        """
        try:
            # Get baseline system memory
            mem = psutil.virtual_memory()
            self.baseline_ram_mb = mem.used / (1024 * 1024)
            self.baseline_ram_percent = mem.percent
            self.peak_ram_mb = self.baseline_ram_mb
            self.peak_ram_percent = self.baseline_ram_percent
            
            # Warm-up call for CPU monitoring
            psutil.cpu_percent(interval=None, percpu=False)
            
            # Initialize sample lists
            self.cpu_samples = []
            self.ram_samples = []
            
            # Start monitoring
            self.monitoring = True
            
            # Start background sampling thread
            self._monitor_thread = threading.Thread(target=self._sample_resources, daemon=True)
            self._monitor_thread.start()
            
        except Exception as e:
            self.monitoring = False
            raise RuntimeError(f"Failed to start monitoring: {e}")
    
    def _sample_resources(self):
        """
        Internal method to sample system-wide resources periodically.
        Runs in background thread during monitoring.
        Samples every 0.5 seconds.
        """
        while self.monitoring:
            try:
                # Sample system-wide RAM
                mem = psutil.virtual_memory()
                current_ram_mb = mem.used / (1024 * 1024)
                current_ram_percent = mem.percent
                
                # Track peak RAM
                if current_ram_mb > self.peak_ram_mb:
                    self.peak_ram_mb = current_ram_mb
                    self.peak_ram_percent = current_ram_percent
                
                # Store RAM delta (increase from baseline)
                ram_delta_mb = current_ram_mb - self.baseline_ram_mb
                self.ram_samples.append(ram_delta_mb)
                
                # Sample system-wide CPU (all cores combined)
                cpu_percent = psutil.cpu_percent(interval=None, percpu=False)
                
                # Keep ALL samples (including zeros)
                self.cpu_samples.append(cpu_percent)
                
                # Sample every 0.5 seconds
                time.sleep(0.5)
                
            except Exception as e:
                # Continue monitoring even if a single sample fails
                print(f"Warning: Resource sampling error: {e}")
                time.sleep(0.5)
    
    def stop_monitoring(self) -> dict:
        """
        Stop monitoring and return metrics.
        
        Returns:
            dict: {
                'peak_ram_mb': float - Peak RAM increase from baseline
                'avg_cpu_percent': float - Average system CPU usage
                'peak_cpu_percent': float - Peak system CPU usage
                'sample_count': int - Number of samples collected
            }
        """
        try:
            # Stop sampling thread
            self.monitoring = False
            
            # Wait for thread to finish (with timeout)
            if self._monitor_thread and self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=1.0)
            
            # Calculate RAM delta (peak increase from baseline)
            peak_ram_delta = self.peak_ram_mb - self.baseline_ram_mb if self.peak_ram_mb else 0
            
            # Calculate average RAM delta
            avg_ram_delta = sum(self.ram_samples) / len(self.ram_samples) if self.ram_samples else 0
            
            # Calculate CPU metrics
            if self.cpu_samples:
                avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples)
                peak_cpu = max(self.cpu_samples)
                sample_count = len(self.cpu_samples)
            else:
                avg_cpu = 0
                peak_cpu = 0
                sample_count = 0
            
            # Return metrics dict
            return {
                'peak_ram_mb': round(peak_ram_delta, 2),
                'avg_cpu_percent': round(avg_cpu, 2),
                'peak_cpu_percent': round(peak_cpu, 2),
                'sample_count': sample_count
            }
            
        except Exception as e:
            # Return default metrics on error
            return {
                'peak_ram_mb': 0,
                'avg_cpu_percent': 0,
                'peak_cpu_percent': 0,
                'sample_count': 0
            }
