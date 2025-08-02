"""Metrics collector for stress testing with detailed performance analysis."""

import asyncio
import contextlib
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class LatencyMetrics:
    """Latency metrics for a specific operation."""
    samples: deque = field(default_factory=lambda: deque(maxlen=10000))
    
    def add_sample(self, latency: float):
        """Add a latency sample in seconds."""
        self.samples.append(latency)
        
    def get_percentiles(self) -> Dict[str, float]:
        """Get latency percentiles in milliseconds."""
        if not self.samples:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0, "p99.9": 0}
            
        sorted_samples = sorted(self.samples)
        n = len(sorted_samples)
        
        return {
            "p50": sorted_samples[int(n * 0.5)] * 1000,
            "p90": sorted_samples[int(n * 0.9)] * 1000,
            "p95": sorted_samples[int(n * 0.95)] * 1000,
            "p99": sorted_samples[int(n * 0.99)] * 1000,
            "p99.9": sorted_samples[int(n * 0.999)] * 1000 if n > 1000 else sorted_samples[-1] * 1000
        }
        
    def get_stats(self) -> Dict[str, float]:
        """Get basic statistics."""
        if not self.samples:
            return {"min": 0, "max": 0, "mean": 0, "std": 0}
            
        samples_ms = [s * 1000 for s in self.samples]
        return {
            "min": min(samples_ms),
            "max": max(samples_ms),
            "mean": np.mean(samples_ms),
            "std": np.std(samples_ms)
        }


@dataclass
class ErrorMetrics:
    """Error tracking metrics."""
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_samples: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """Add an error sample."""
        self.errors_by_type[error_type] += 1
        self.error_samples.append({
            "timestamp": datetime.now(),
            "type": error_type,
            "message": error_message,
            "context": context or {}
        })
        
    def get_error_rate(self, total_requests: int) -> float:
        """Get overall error rate."""
        if total_requests == 0:
            return 0.0
        total_errors = sum(self.errors_by_type.values())
        return (total_errors / total_requests) * 100


@dataclass
class ThroughputMetrics:
    """Throughput tracking metrics."""
    request_times: deque = field(default_factory=lambda: deque(maxlen=10000))
    window_size: int = 60  # 1 minute window
    
    def add_request(self, timestamp: Optional[float] = None):
        """Add a request timestamp."""
        self.request_times.append(timestamp or time.time())
        
    def get_current_rps(self) -> float:
        """Get current requests per second."""
        if not self.request_times:
            return 0.0
            
        now = time.time()
        recent_requests = [t for t in self.request_times if now - t <= self.window_size]
        
        if len(recent_requests) < 2:
            return 0.0
            
        time_span = now - recent_requests[0]
        return len(recent_requests) / time_span
        
    def get_peak_rps(self) -> float:
        """Get peak RPS in 1-second windows."""
        if len(self.request_times) < 2:
            return 0.0
            
        # Count requests in 1-second buckets
        buckets = defaultdict(int)
        for timestamp in self.request_times:
            bucket = int(timestamp)
            buckets[bucket] += 1
            
        return max(buckets.values()) if buckets else 0.0


class MetricsCollector:
    """Comprehensive metrics collector for stress testing."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = None
        self.end_time = None
        
        # Latency metrics by operation type
        self.latencies = {
            "overall": LatencyMetrics(),
            "text_message": LatencyMetrics(),
            "voice_message": LatencyMetrics(),
            "command": LatencyMetrics(),
            "callback": LatencyMetrics(),
            "edit_message": LatencyMetrics(),
            "openai_api": LatencyMetrics(),
            "deepgram_api": LatencyMetrics(),
            "todoist_api": LatencyMetrics()
        }
        
        # Error metrics
        self.errors = ErrorMetrics()
        
        # Throughput metrics
        self.throughput = ThroughputMetrics()
        
        # Counters
        self.counters = defaultdict(int)
        
        # Resource usage
        self.resource_samples = []
        
        # Active requests tracking
        self.active_requests = 0
        self.max_concurrent_requests = 0
        
    def start_test(self):
        """Mark test start."""
        self.start_time = time.time()
        
    def end_test(self):
        """Mark test end."""
        self.end_time = time.time()
        
    @contextlib.asynccontextmanager
    async def track_request(self, operation_type: str):
        """Context manager to track request latency."""
        start_time = time.time()
        self.active_requests += 1
        self.max_concurrent_requests = max(self.max_concurrent_requests, self.active_requests)
        
        try:
            yield
            
            # Record success
            latency = time.time() - start_time
            self.latencies["overall"].add_sample(latency)
            if operation_type in self.latencies:
                self.latencies[operation_type].add_sample(latency)
                
            self.counters[f"{operation_type}_success"] += 1
            self.throughput.add_request()
            
        except Exception as e:
            # Record error
            self.errors.add_error(
                type(e).__name__,
                str(e),
                {"operation": operation_type}
            )
            self.counters[f"{operation_type}_error"] += 1
            raise
            
        finally:
            self.active_requests -= 1
            
    def track_external_api_call(self, api_name: str, latency: float, success: bool):
        """Track external API call metrics."""
        metric_key = f"{api_name}_api"
        if metric_key in self.latencies:
            self.latencies[metric_key].add_sample(latency)
            
        if success:
            self.counters[f"{api_name}_success"] += 1
        else:
            self.counters[f"{api_name}_error"] += 1
            
    def add_resource_sample(self, cpu_percent: float, memory_mb: float, redis_connections: int):
        """Add resource usage sample."""
        self.resource_samples.append({
            "timestamp": time.time(),
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "redis_connections": redis_connections
        })
        
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        if not self.start_time:
            return {"error": "Test not started"}
            
        test_duration = (self.end_time or time.time()) - self.start_time
        total_requests = self.counters.get("overall_success", 0) + sum(
            v for k, v in self.counters.items() if k.endswith("_error")
        )
        
        # Calculate success rate
        success_rate = 0.0
        if total_requests > 0:
            total_success = sum(v for k, v in self.counters.items() if k.endswith("_success"))
            success_rate = (total_success / total_requests) * 100
            
        # Get latency stats
        latency_stats = {}
        for name, metrics in self.latencies.items():
            if metrics.samples:
                latency_stats[name] = {
                    **metrics.get_percentiles(),
                    **metrics.get_stats()
                }
                
        # Get resource usage stats
        resource_stats = {}
        if self.resource_samples:
            cpu_values = [s["cpu_percent"] for s in self.resource_samples]
            memory_values = [s["memory_mb"] for s in self.resource_samples]
            redis_values = [s["redis_connections"] for s in self.resource_samples]
            
            resource_stats = {
                "cpu": {
                    "avg": np.mean(cpu_values),
                    "max": max(cpu_values),
                    "p95": np.percentile(cpu_values, 95)
                },
                "memory_mb": {
                    "avg": np.mean(memory_values),
                    "max": max(memory_values)
                },
                "redis_connections": {
                    "avg": np.mean(redis_values),
                    "max": max(redis_values)
                }
            }
            
        return {
            "test_duration_seconds": test_duration,
            "total_requests": total_requests,
            "success_rate": success_rate,
            "throughput": {
                "average_rps": total_requests / test_duration if test_duration > 0 else 0,
                "current_rps": self.throughput.get_current_rps(),
                "peak_rps": self.throughput.get_peak_rps()
            },
            "latency": latency_stats,
            "errors": {
                "total": sum(self.errors.errors_by_type.values()),
                "rate": self.errors.get_error_rate(total_requests),
                "by_type": dict(self.errors.errors_by_type),
                "samples": self.errors.error_samples[:10]  # First 10 errors
            },
            "counters": dict(self.counters),
            "concurrency": {
                "max_concurrent_requests": self.max_concurrent_requests
            },
            "resources": resource_stats
        }
        
    def print_summary(self):
        """Print formatted metrics summary."""
        summary = self.get_summary()
        
        print("\n" + "="*80)
        print("STRESS TEST METRICS SUMMARY")
        print("="*80)
        
        # Basic stats
        print(f"\nTest Duration: {summary['test_duration_seconds']:.2f} seconds")
        print(f"Total Requests: {summary['total_requests']:,}")
        print(f"Success Rate: {summary['success_rate']:.2f}%")
        
        # Throughput
        print(f"\nThroughput:")
        print(f"  Average: {summary['throughput']['average_rps']:.2f} req/s")
        print(f"  Current: {summary['throughput']['current_rps']:.2f} req/s")
        print(f"  Peak: {summary['throughput']['peak_rps']:.2f} req/s")
        
        # Latency
        print(f"\nLatency (Overall):")
        if "overall" in summary["latency"]:
            overall = summary["latency"]["overall"]
            print(f"  P50: {overall['p50']:.2f}ms")
            print(f"  P90: {overall['p90']:.2f}ms")
            print(f"  P95: {overall['p95']:.2f}ms")
            print(f"  P99: {overall['p99']:.2f}ms")
            print(f"  P99.9: {overall.get('p99.9', 0):.2f}ms")
            print(f"  Mean: {overall['mean']:.2f}ms (±{overall['std']:.2f}ms)")
            
        # Errors
        print(f"\nErrors:")
        print(f"  Total: {summary['errors']['total']}")
        print(f"  Error Rate: {summary['errors']['rate']:.2f}%")
        if summary['errors']['by_type']:
            print("  By Type:")
            for error_type, count in summary['errors']['by_type'].items():
                print(f"    - {error_type}: {count}")
                
        # Resources
        if summary.get('resources'):
            print(f"\nResource Usage:")
            print(f"  CPU: avg={summary['resources']['cpu']['avg']:.1f}%, max={summary['resources']['cpu']['max']:.1f}%")
            print(f"  Memory: avg={summary['resources']['memory_mb']['avg']:.1f}MB, max={summary['resources']['memory_mb']['max']:.1f}MB")
            
        print("="*80)