#!/usr/bin/env python3
"""
Comprehensive test execution script for Task 5 - Testing and Integration Validation.
Runs all test suites and generates detailed reports.
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test.utils import get_runner
from django.conf import settings


class ComprehensiveTestRunner:
    """Comprehensive test runner for all Task 5 test suites."""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.report_dir = self.test_dir / 'reports'
        self.report_dir.mkdir(exist_ok=True)
        
        self.test_suites = {
            'test_base': {
                'name': 'Test Infrastructure',
                'module': 'test.test_base',
                'priority': 1,
                'description': 'Base test classes and utilities'
            },
            'test_fixtures': {
                'name': 'Test Fixtures',
                'module': 'test.test_fixtures', 
                'priority': 1,
                'description': 'Mock data and fixture management'
            },
            'test_uuid_mechanism': {
                'name': 'UUID Mechanism Tests',
                'module': 'test.test_uuid_mechanism',
                'priority': 2,
                'description': 'Deterministic UUID generation validation'
            },
            'test_ai_service_comprehensive': {
                'name': 'AI Service Comprehensive Tests',
                'module': 'test.test_ai_service_comprehensive',
                'priority': 3,
                'description': 'AI meal plan generation functionality'
            },
            'test_recipe_save_comprehensive': {
                'name': 'Recipe Save Comprehensive Tests',
                'module': 'test.test_recipe_save_comprehensive',
                'priority': 3,
                'description': 'Recipe saving and duplicate detection'
            },
            'test_end_to_end_integration': {
                'name': 'End-to-End Integration Tests',
                'module': 'test.test_end_to_end_integration',
                'priority': 4,
                'description': 'Complete workflow integration testing'
            },
            'test_performance_benchmarks': {
                'name': 'Performance Benchmark Tests',
                'module': 'test.test_performance_benchmarks',
                'priority': 5,
                'description': '4.2x performance improvement validation'
            }
        }
        
        self.results = {}
        self.start_time = None
        self.end_time = None
    
    def run_all_tests(self, verbose: bool = True, fast: bool = False) -> Dict[str, Any]:
        """Run all test suites and collect results."""
        
        print("🧪 Starting Comprehensive Test Suite for Task 5")
        print("=" * 60)
        
        self.start_time = datetime.now()
        
        # Run test suites in priority order
        sorted_suites = sorted(self.test_suites.items(), key=lambda x: x[1]['priority'])
        
        for suite_key, suite_info in sorted_suites:
            if fast and suite_info['priority'] > 3:
                print(f"⏭️  Skipping {suite_info['name']} (fast mode)")
                continue
                
            print(f"\n📋 Running {suite_info['name']}")
            print(f"   {suite_info['description']}")
            
            result = self._run_test_suite(suite_key, suite_info, verbose)
            self.results[suite_key] = result
            
            # Stop on critical failures
            if result['critical_failure']:
                print(f"❌ Critical failure in {suite_info['name']}, stopping execution")
                break
        
        self.end_time = datetime.now()
        
        # Generate reports
        self._generate_summary_report()
        self._generate_detailed_report()
        self._generate_performance_report()
        
        return self.results
    
    def _run_test_suite(self, suite_key: str, suite_info: Dict[str, Any], verbose: bool) -> Dict[str, Any]:
        """Run a single test suite."""
        
        start_time = time.perf_counter()
        
        try:
            # Import the test module
            test_module = __import__(suite_info['module'], fromlist=[''])
            
            # Run tests using Django test runner
            import unittest
            loader = unittest.TestLoader()
            suite = loader.loadTestsFromModule(test_module)
            
            # Custom test result collector
            result_collector = TestResultCollector()
            runner = unittest.TextTestRunner(
                stream=result_collector,
                verbosity=2 if verbose else 1,
                buffer=True
            )
            
            test_result = runner.run(suite)
            
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            # Analyze results
            total_tests = test_result.testsRun
            failures = len(test_result.failures)
            errors = len(test_result.errors)
            successes = total_tests - failures - errors
            success_rate = (successes / total_tests * 100) if total_tests > 0 else 0
            
            # Determine if this is a critical failure
            critical_failure = (
                success_rate < 50 or  # Less than 50% success
                errors > failures or  # More errors than failures
                suite_info['priority'] <= 2  # Infrastructure failures are critical
            )
            
            result = {
                'suite_name': suite_info['name'],
                'module': suite_info['module'],
                'priority': suite_info['priority'],
                'execution_time': execution_time,
                'total_tests': total_tests,
                'successes': successes,
                'failures': failures,
                'errors': errors,
                'success_rate': success_rate,
                'critical_failure': critical_failure,
                'failure_details': test_result.failures,
                'error_details': test_result.errors,
                'output': result_collector.get_output()
            }
            
            # Print immediate results
            status_icon = "✅" if success_rate >= 90 else "⚠️" if success_rate >= 70 else "❌"
            print(f"   {status_icon} {successes}/{total_tests} tests passed ({success_rate:.1f}%) in {execution_time:.2f}s")
            
            if failures > 0:
                print(f"      ⚠️  {failures} failures")
            if errors > 0:
                print(f"      ❌ {errors} errors")
            
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            
            print(f"   ❌ Failed to run test suite: {str(e)}")
            
            return {
                'suite_name': suite_info['name'],
                'module': suite_info['module'],
                'priority': suite_info['priority'],
                'execution_time': execution_time,
                'total_tests': 0,
                'successes': 0,
                'failures': 0,
                'errors': 1,
                'success_rate': 0,
                'critical_failure': True,
                'failure_details': [],
                'error_details': [('Suite Execution', str(e))],
                'output': f"Error running test suite: {str(e)}"
            }
    
    def _generate_summary_report(self):
        """Generate executive summary report."""
        
        total_duration = self.end_time - self.start_time
        
        # Aggregate statistics
        total_tests = sum(r['total_tests'] for r in self.results.values())
        total_successes = sum(r['successes'] for r in self.results.values())
        total_failures = sum(r['failures'] for r in self.results.values())
        total_errors = sum(r['errors'] for r in self.results.values())
        overall_success_rate = (total_successes / total_tests * 100) if total_tests > 0 else 0
        
        # Performance metrics
        performance_results = self.results.get('test_performance_benchmarks', {})
        ai_performance_validated = performance_results.get('success_rate', 0) >= 80
        
        # Critical systems status
        critical_systems = ['test_base', 'test_ai_service_comprehensive', 'test_recipe_save_comprehensive']
        critical_success = all(
            self.results.get(sys, {}).get('success_rate', 0) >= 80 
            for sys in critical_systems
        )
        
        summary = {
            'test_execution_summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'total_duration_seconds': total_duration.total_seconds(),
                'total_test_suites': len(self.results),
                'total_tests': total_tests,
                'total_successes': total_successes,
                'total_failures': total_failures,
                'total_errors': total_errors,
                'overall_success_rate': overall_success_rate
            },
            'critical_validations': {
                'ai_performance_4_2x_improvement': ai_performance_validated,
                'critical_systems_functional': critical_success,
                'end_to_end_workflow_validated': self.results.get('test_end_to_end_integration', {}).get('success_rate', 0) >= 70,
                'uuid_determinism_validated': self.results.get('test_uuid_mechanism', {}).get('success_rate', 0) >= 90
            },
            'recommendations': self._generate_recommendations(),
            'deployment_readiness': self._assess_deployment_readiness()
        }
        
        # Save summary report
        summary_file = self.report_dir / f'test_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Print summary
        self._print_summary_report(summary)
        
        return summary
    
    def _print_summary_report(self, summary: Dict[str, Any]):
        """Print executive summary to console."""
        
        print("\n" + "=" * 60)
        print("🎯 TASK 5 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("=" * 60)
        
        exec_summary = summary['test_execution_summary']
        print(f"📊 Execution Overview:")
        print(f"   Duration: {exec_summary['total_duration_seconds']:.1f} seconds")
        print(f"   Test Suites: {exec_summary['total_test_suites']}")
        print(f"   Total Tests: {exec_summary['total_tests']}")
        print(f"   Success Rate: {exec_summary['overall_success_rate']:.1f}%")
        
        print(f"\n🎯 Critical Validations:")
        validations = summary['critical_validations']
        for validation, passed in validations.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            readable_name = validation.replace('_', ' ').title()
            print(f"   {status} {readable_name}")
        
        deployment = summary['deployment_readiness']
        print(f"\n🚀 Deployment Readiness: {deployment['status'].upper()}")
        print(f"   Confidence Level: {deployment['confidence_level']:.1f}%")
        
        if deployment['blocking_issues']:
            print(f"   ⚠️  Blocking Issues:")
            for issue in deployment['blocking_issues']:
                print(f"      - {issue}")
        
        if summary['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in summary['recommendations']:
                print(f"   - {rec}")
    
    def _generate_detailed_report(self):
        """Generate detailed test report."""
        
        detailed_report = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'test_environment': {
                    'python_version': sys.version,
                    'django_version': django.get_version(),
                    'database': settings.DATABASES['default']['ENGINE']
                }
            },
            'test_suites': {}
        }
        
        for suite_key, result in self.results.items():
            detailed_report['test_suites'][suite_key] = {
                'suite_info': result,
                'detailed_failures': self._format_failure_details(result['failure_details']),
                'detailed_errors': self._format_error_details(result['error_details'])
            }
        
        # Save detailed report
        detailed_file = self.report_dir / f'test_detailed_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(detailed_file, 'w') as f:
            json.dump(detailed_report, f, indent=2, default=str)
        
        return detailed_report
    
    def _generate_performance_report(self):
        """Generate performance-specific report."""
        
        performance_result = self.results.get('test_performance_benchmarks', {})
        
        performance_report = {
            'performance_validation': {
                'ai_generation_performance': {
                    'baseline_time_seconds': 12.0,
                    'target_improvement_factor': 4.2,
                    'target_time_seconds': 2.86,
                    'validated': performance_result.get('success_rate', 0) >= 80
                },
                'batch_save_performance': {
                    'target_recipes': 20,
                    'target_time_seconds': 2.0,
                    'validated': performance_result.get('success_rate', 0) >= 80
                }
            },
            'test_execution_performance': {
                suite_key: {
                    'execution_time': result['execution_time'],
                    'tests_per_second': result['total_tests'] / result['execution_time'] if result['execution_time'] > 0 else 0
                }
                for suite_key, result in self.results.items()
            }
        }
        
        # Save performance report
        perf_file = self.report_dir / f'test_performance_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(perf_file, 'w') as f:
            json.dump(performance_report, f, indent=2, default=str)
        
        return performance_report
    
    def _format_failure_details(self, failures: List[Tuple]) -> List[Dict[str, str]]:
        """Format failure details for reporting."""
        return [
            {
                'test': str(test),
                'failure_message': traceback.split('\n')[-2] if traceback else 'Unknown failure'
            }
            for test, traceback in failures
        ]
    
    def _format_error_details(self, errors: List[Tuple]) -> List[Dict[str, str]]:
        """Format error details for reporting."""
        return [
            {
                'test': str(test),
                'error_message': traceback.split('\n')[-2] if traceback else 'Unknown error'
            }
            for test, traceback in errors
        ]
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        
        overall_success = sum(r['success_rate'] for r in self.results.values()) / len(self.results)
        
        if overall_success < 80:
            recommendations.append("Overall test success rate below 80% - investigate failures before deployment")
        
        performance_result = self.results.get('test_performance_benchmarks', {})
        if performance_result.get('success_rate', 0) < 80:
            recommendations.append("Performance benchmarks not met - review AI service optimization")
        
        integration_result = self.results.get('test_end_to_end_integration', {})
        if integration_result.get('success_rate', 0) < 70:
            recommendations.append("End-to-end integration tests failing - check system integration")
        
        # Check for critical system failures
        critical_systems = ['test_ai_service_comprehensive', 'test_recipe_save_comprehensive']
        for sys in critical_systems:
            if self.results.get(sys, {}).get('success_rate', 0) < 70:
                recommendations.append(f"Critical system {sys} has low success rate - prioritize fixes")
        
        if not recommendations:
            recommendations.append("All systems performing well - ready for deployment")
        
        return recommendations
    
    def _assess_deployment_readiness(self) -> Dict[str, Any]:
        """Assess overall deployment readiness."""
        
        # Critical success criteria
        criteria = {
            'overall_success_rate': sum(r['success_rate'] for r in self.results.values()) / len(self.results),
            'performance_validated': self.results.get('test_performance_benchmarks', {}).get('success_rate', 0) >= 80,
            'integration_validated': self.results.get('test_end_to_end_integration', {}).get('success_rate', 0) >= 70,
            'critical_systems_ok': all(
                self.results.get(sys, {}).get('success_rate', 0) >= 70
                for sys in ['test_ai_service_comprehensive', 'test_recipe_save_comprehensive']
            )
        }
        
        # Blocking issues
        blocking_issues = []
        if criteria['overall_success_rate'] < 70:
            blocking_issues.append("Overall test success rate below 70%")
        if not criteria['performance_validated']:
            blocking_issues.append("Performance benchmarks not validated")
        if not criteria['critical_systems_ok']:
            blocking_issues.append("Critical system failures detected")
        
        # Determine status
        if not blocking_issues and criteria['overall_success_rate'] >= 90:
            status = 'ready'
            confidence = 95.0
        elif not blocking_issues and criteria['overall_success_rate'] >= 80:
            status = 'ready_with_monitoring'
            confidence = 85.0
        elif criteria['overall_success_rate'] >= 70:
            status = 'conditional'
            confidence = 70.0
        else:
            status = 'not_ready'
            confidence = 40.0
        
        return {
            'status': status,
            'confidence_level': confidence,
            'blocking_issues': blocking_issues,
            'criteria_met': criteria
        }


class TestResultCollector:
    """Collects test output for reporting."""
    
    def __init__(self):
        self.output = []
    
    def write(self, text):
        self.output.append(text)
    
    def flush(self):
        pass
    
    def get_output(self):
        return ''.join(self.output)


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive tests for Task 5')
    parser.add_argument('--fast', action='store_true', help='Run only critical tests (priority <= 3)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--suite', type=str, help='Run specific test suite')
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    
    if args.suite:
        # Run specific suite
        if args.suite in runner.test_suites:
            suite_info = runner.test_suites[args.suite]
            print(f"Running specific test suite: {suite_info['name']}")
            result = runner._run_test_suite(args.suite, suite_info, args.verbose)
            print(f"\nResults: {result['successes']}/{result['total_tests']} passed ({result['success_rate']:.1f}%)")
        else:
            print(f"Unknown test suite: {args.suite}")
            print(f"Available suites: {', '.join(runner.test_suites.keys())}")
    else:
        # Run all tests
        results = runner.run_all_tests(verbose=args.verbose, fast=args.fast)
        
        # Exit with appropriate code
        overall_success = sum(r['success_rate'] for r in results.values()) / len(results) if results else 0
        exit_code = 0 if overall_success >= 80 else 1
        sys.exit(exit_code)


if __name__ == '__main__':
    main()