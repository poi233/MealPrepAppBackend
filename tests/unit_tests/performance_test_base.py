#!/usr/bin/env python3
"""
Performance testing framework for comprehensive benchmarking.
Provides tools for measuring and validating performance improvements.
"""

import os
import sys
import time
import json
import statistics
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed

import django
from django.conf import settings

# Setup Django if not already done
if not settings.configured:
    sys.path.insert(0, '/Users/puyihao/workspace/MealPrep/MealPrepAppBackend/src')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()


@dataclass
class PerformanceMetrics:
    """Container for performance measurement data."""
    operation_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    timestamp: datetime
    thread_id: int
    success: bool
    error_message: Optional[str] = None
    custom_metrics: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class PerformanceBenchmark:
    """Performance benchmark definition."""
    name: str
    baseline_time: float
    target_improvement_factor: float
    max_acceptable_time: float
    max_memory_mb: Optional[float] = None
    max_cpu_percent: Optional[float] = None
    
    def validate_metrics(self, metrics: PerformanceMetrics) -> Tuple[bool, List[str]]:
        """Validate metrics against benchmark criteria."""
        issues = []
        
        if metrics.execution_time > self.max_acceptable_time:
            issues.append(
                f"Execution time {metrics.execution_time:.3f}s exceeds limit {self.max_acceptable_time:.3f}s"
            )
        
        expected_max_time = self.baseline_time / self.target_improvement_factor
        if metrics.execution_time > expected_max_time:
            issues.append(
                f"Performance improvement not met: {metrics.execution_time:.3f}s > {expected_max_time:.3f}s "
                f"(expected {self.target_improvement_factor}x improvement)"
            )
        
        if self.max_memory_mb and metrics.memory_usage_mb > self.max_memory_mb:
            issues.append(
                f"Memory usage {metrics.memory_usage_mb:.1f}MB exceeds limit {self.max_memory_mb:.1f}MB"
            )
        
        if self.max_cpu_percent and metrics.cpu_usage_percent > self.max_cpu_percent:
            issues.append(
                f"CPU usage {metrics.cpu_usage_percent:.1f}% exceeds limit {self.max_cpu_percent:.1f}%"
            )
        
        return len(issues) == 0, issues


class PerformanceTracker:
    """Tracks performance metrics during test execution."""
    
    def __init__(self):
        self.metrics: List[PerformanceMetrics] = []
        self.process = psutil.Process()
        self._lock = threading.Lock()
    
    @contextmanager
    def measure_operation(self, operation_name: str, **custom_metrics):
        """Context manager for measuring operation performance."""
        # Pre-measurement setup
        initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        initial_cpu_times = self.process.cpu_times()
        start_time = time.perf_counter()
        thread_id = threading.get_ident()
        
        success = False
        error_message = None
        
        try:
            yield
            success = True
        except Exception as e:
            error_message = str(e)
            raise
        finally:
            # Post-measurement calculation
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            final_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            memory_usage = max(final_memory - initial_memory, 0)
            
            # CPU usage calculation (simplified)
            final_cpu_times = self.process.cpu_times()
            cpu_time_used = (final_cpu_times.user + final_cpu_times.system) - \
                           (initial_cpu_times.user + initial_cpu_times.system)
            cpu_usage_percent = (cpu_time_used / execution_time * 100) if execution_time > 0 else 0
            
            metrics = PerformanceMetrics(
                operation_name=operation_name,
                execution_time=execution_time,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage_percent,
                timestamp=datetime.now(),
                thread_id=thread_id,
                success=success,
                error_message=error_message,
                custom_metrics=custom_metrics or None
            )
            
            with self._lock:
                self.metrics.append(metrics)
    
    def get_metrics_for_operation(self, operation_name: str) -> List[PerformanceMetrics]:
        """Get all metrics for a specific operation."""
        return [m for m in self.metrics if m.operation_name == operation_name]
    
    def get_aggregate_stats(self, operation_name: str) -> Dict[str, float]:
        """Get aggregate statistics for an operation."""
        operation_metrics = self.get_metrics_for_operation(operation_name)
        if not operation_metrics:
            return {}
        
        execution_times = [m.execution_time for m in operation_metrics if m.success]
        memory_usage = [m.memory_usage_mb for m in operation_metrics if m.success]
        cpu_usage = [m.cpu_usage_percent for m in operation_metrics if m.success]
        
        if not execution_times:
            return {'success_rate': 0.0}
        
        return {
            'count': len(operation_metrics),
            'success_count': len(execution_times),
            'success_rate': len(execution_times) / len(operation_metrics),
            'avg_execution_time': statistics.mean(execution_times),
            'median_execution_time': statistics.median(execution_times),
            'min_execution_time': min(execution_times),
            'max_execution_time': max(execution_times),
            'stdev_execution_time': statistics.stdev(execution_times) if len(execution_times) > 1 else 0,
            'avg_memory_usage_mb': statistics.mean(memory_usage) if memory_usage else 0,
            'avg_cpu_usage_percent': statistics.mean(cpu_usage) if cpu_usage else 0
        }
    
    def clear_metrics(self):
        """Clear all collected metrics."""
        with self._lock:
            self.metrics.clear()
    
    def export_metrics(self, filepath: str):
        """Export metrics to JSON file."""
        data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_metrics': len(self.metrics),
            'metrics': [m.to_dict() for m in self.metrics]
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


class LoadTestRunner:
    """Runner for load and stress testing."""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.tracker = PerformanceTracker()
    
    def run_load_test(self, 
                     operation: Callable,
                     concurrent_users: int,
                     operations_per_user: int,
                     ramp_up_seconds: float = 0,
                     timeout: float = 300) -> Dict[str, Any]:
        """Run a load test with specified parameters."""
        
        total_operations = concurrent_users * operations_per_user
        results = {
            'test_config': {
                'concurrent_users': concurrent_users,
                'operations_per_user': operations_per_user,
                'total_operations': total_operations,
                'ramp_up_seconds': ramp_up_seconds,
                'timeout': timeout
            },
            'start_time': datetime.now().isoformat(),
            'operations_completed': 0,
            'operations_failed': 0,
            'errors': []
        }
        
        def user_operation(user_id: int):
            """Operation executed by each simulated user."""
            user_results = {'completed': 0, 'failed': 0, 'errors': []}
            
            for op_id in range(operations_per_user):
                operation_name = f"load_test_user_{user_id}_op_{op_id}"
                
                try:
                    with self.tracker.measure_operation(operation_name):
                        operation()
                    user_results['completed'] += 1
                except Exception as e:
                    user_results['failed'] += 1
                    user_results['errors'].append(str(e))
            
            return user_results
        
        # Execute load test
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=min(concurrent_users, self.max_workers)) as executor:
            # Submit all user operations
            futures = []
            for user_id in range(concurrent_users):
                # Implement ramp-up delay
                if ramp_up_seconds > 0:
                    delay = (user_id / concurrent_users) * ramp_up_seconds
                    time.sleep(delay)
                
                future = executor.submit(user_operation, user_id)
                futures.append(future)
            
            # Collect results
            try:
                for future in as_completed(futures, timeout=timeout):
                    user_result = future.result()
                    results['operations_completed'] += user_result['completed']
                    results['operations_failed'] += user_result['failed']
                    results['errors'].extend(user_result['errors'])
            
            except Exception as e:
                results['errors'].append(f"Load test execution error: {str(e)}")
        
        end_time = time.perf_counter()
        results['end_time'] = datetime.now().isoformat()
        results['total_duration'] = end_time - start_time
        results['throughput_ops_per_second'] = results['operations_completed'] / results['total_duration']
        
        return results
    
    def run_stress_test(self,
                       operation: Callable,
                       max_concurrent_users: int,
                       step_size: int = 5,
                       step_duration: int = 30,
                       operations_per_user: int = 10) -> Dict[str, Any]:
        """Run a stress test with gradually increasing load."""
        
        stress_results = {
            'test_config': {
                'max_concurrent_users': max_concurrent_users,
                'step_size': step_size,
                'step_duration': step_duration,
                'operations_per_user': operations_per_user
            },
            'steps': [],
            'breaking_point': None
        }
        
        current_users = step_size
        
        while current_users <= max_concurrent_users:
            print(f"🧪 Running stress test step: {current_users} concurrent users")
            
            step_result = self.run_load_test(
                operation=operation,
                concurrent_users=current_users,
                operations_per_user=operations_per_user,
                timeout=step_duration * 2
            )
            
            step_result['concurrent_users'] = current_users
            step_result['success_rate'] = (
                step_result['operations_completed'] / 
                (step_result['operations_completed'] + step_result['operations_failed'])
                if (step_result['operations_completed'] + step_result['operations_failed']) > 0 else 0
            )
            
            stress_results['steps'].append(step_result)
            
            # Check if we hit breaking point (success rate < 95%)
            if step_result['success_rate'] < 0.95:
                stress_results['breaking_point'] = current_users
                print(f"💥 Breaking point reached at {current_users} concurrent users")
                break
            
            current_users += step_size
        
        return stress_results


class PerformanceTestCase:
    """Base class for performance testing."""
    
    def __init__(self):
        self.tracker = PerformanceTracker()
        self.benchmarks: Dict[str, PerformanceBenchmark] = {}
        self.load_runner = LoadTestRunner()
    
    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add a performance benchmark."""
        self.benchmarks[benchmark.name] = benchmark
    
    def measure_operation(self, operation_name: str, **custom_metrics):
        """Context manager for measuring operations."""
        return self.tracker.measure_operation(operation_name, **custom_metrics)
    
    def assert_performance_benchmark(self, operation_name: str, benchmark_name: str):
        """Assert that operation meets performance benchmark."""
        benchmark = self.benchmarks.get(benchmark_name)
        if not benchmark:
            raise ValueError(f"Benchmark '{benchmark_name}' not found")
        
        metrics = self.tracker.get_metrics_for_operation(operation_name)
        if not metrics:
            raise ValueError(f"No metrics found for operation '{operation_name}'")
        
        # Use the most recent successful metric
        successful_metrics = [m for m in metrics if m.success]
        if not successful_metrics:
            raise AssertionError(f"No successful executions for operation '{operation_name}'")
        
        latest_metric = max(successful_metrics, key=lambda m: m.timestamp)
        is_valid, issues = benchmark.validate_metrics(latest_metric)
        
        if not is_valid:
            raise AssertionError(f"Performance benchmark failed for '{operation_name}':\n" + 
                               "\n".join(f"  - {issue}" for issue in issues))
    
    def run_concurrent_operations(self, operation: Callable, count: int, timeout: float = 60):
        """Run multiple operations concurrently and measure performance."""
        operation_name = f"concurrent_{operation.__name__}_{count}_users"
        
        return self.load_runner.run_load_test(
            operation=operation,
            concurrent_users=count,
            operations_per_user=1,
            timeout=timeout
        )
    
    def generate_performance_report(self, filepath: str):
        """Generate comprehensive performance report."""
        report = {
            'generation_time': datetime.now().isoformat(),
            'total_operations': len(self.tracker.metrics),
            'benchmarks': {name: asdict(benchmark) for name, benchmark in self.benchmarks.items()},
            'operations_summary': {}
        }
        
        # Generate summary for each unique operation
        operation_names = set(m.operation_name for m in self.tracker.metrics)
        for op_name in operation_names:
            stats = self.tracker.get_aggregate_stats(op_name)
            report['operations_summary'][op_name] = stats
            
            # Check against benchmarks
            for benchmark_name, benchmark in self.benchmarks.items():
                if benchmark_name in op_name or op_name in benchmark_name:
                    metrics = self.tracker.get_metrics_for_operation(op_name)
                    if metrics:
                        successful_metrics = [m for m in metrics if m.success]
                        if successful_metrics:
                            latest_metric = max(successful_metrics, key=lambda m: m.timestamp)
                            is_valid, issues = benchmark.validate_metrics(latest_metric)
                            stats['benchmark_validation'] = {
                                'benchmark_name': benchmark_name,
                                'passed': is_valid,
                                'issues': issues
                            }
        
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report


# Pre-defined benchmarks for common operations
AI_MEAL_PLAN_BENCHMARK = PerformanceBenchmark(
    name="ai_meal_plan_generation",
    baseline_time=12.0,  # Previous baseline
    target_improvement_factor=4.2,  # Target improvement
    max_acceptable_time=3.0,  # Maximum acceptable time
    max_memory_mb=500.0,  # Memory limit
    max_cpu_percent=90.0   # CPU limit
)

RECIPE_SAVE_BENCHMARK = PerformanceBenchmark(
    name="recipe_save_operation",
    baseline_time=0.5,
    target_improvement_factor=1.0,  # No specific improvement target
    max_acceptable_time=1.0,
    max_memory_mb=100.0,
    max_cpu_percent=50.0
)

BATCH_SAVE_BENCHMARK = PerformanceBenchmark(
    name="batch_recipe_save",
    baseline_time=10.0,
    target_improvement_factor=1.0,
    max_acceptable_time=2.0,  # 20 recipes in under 2 seconds
    max_memory_mb=200.0,
    max_cpu_percent=80.0
)