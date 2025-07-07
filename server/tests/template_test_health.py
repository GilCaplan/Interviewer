#!/usr/bin/env python3
"""
Continuous System Health Monitor for Interview Assistant Platform
Monitors: API health, database connectivity, performance metrics, error rates

Run with: python system_monitor.py
"""

import requests
import time
import json
import threading
from datetime import datetime, timedelta
import statistics
from collections import deque, defaultdict

# Configuration
API_URL = "http://localhost:5000"
MONITOR_INTERVAL = 5  # seconds between checks
METRIC_HISTORY_SIZE = 100  # keep last 100 measurements
ALERT_THRESHOLDS = {
    'response_time': 2.0,  # seconds
    'error_rate': 5.0,  # percentage
    'success_rate': 95.0  # minimum percentage
}


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'


def log(message, color=Colors.CYAN):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{color}[{timestamp}] {message}{Colors.END}")


class PerformanceMetrics:
    """Track performance metrics over time"""

    def __init__(self):
        self.response_times = deque(maxlen=METRIC_HISTORY_SIZE)
        self.success_count = 0
        self.error_count = 0
        self.total_requests = 0
        self.error_types = defaultdict(int)
        self.start_time = datetime.now()

    def record_success(self, response_time):
        """Record a successful request"""
        self.response_times.append(response_time)
        self.success_count += 1
        self.total_requests += 1

    def record_error(self, error_type):
        """Record an error"""
        self.error_count += 1
        self.total_requests += 1
        self.error_types[error_type] += 1

    def get_stats(self):
        """Get current statistics"""
        if not self.response_times:
            return None

        return {
            'avg_response_time': statistics.mean(self.response_times),
            'min_response_time': min(self.response_times),
            'max_response_time': max(self.response_times),
            'median_response_time': statistics.median(self.response_times),
            'success_rate': (self.success_count / self.total_requests * 100) if self.total_requests > 0 else 0,
            'error_rate': (self.error_count / self.total_requests * 100) if self.total_requests > 0 else 0,
            'total_requests': self.total_requests,
            'uptime': datetime.now() - self.start_time
        }


class SystemHealthMonitor:
    """Main system health monitoring class"""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.monitoring = False
        self.alerts_sent = set()
        self.last_health_status = None

    def check_api_health(self):
        """Check API health endpoint"""
        try:
            start_time = time.time()
            response = requests.get(f"{API_URL}/api/health", timeout=10)
            response_time = time.time() - start_time

            if response.status_code == 200:
                self.metrics.record_success(response_time)
                return True, response_time, response.json()
            else:
                self.metrics.record_error(f"HTTP_{response.status_code}")
                return False, response_time, None

        except requests.exceptions.Timeout:
            self.metrics.record_error("TIMEOUT")
            return False, 10.0, None
        except requests.exceptions.ConnectionError:
            self.metrics.record_error("CONNECTION_ERROR")
            return False, 0, None
        except Exception as e:
            self.metrics.record_error(f"EXCEPTION_{type(e).__name__}")
            return False, 0, None

    def test_api_endpoints(self):
        """Test various API endpoints"""
        endpoints = [
            ("/api/info", "GET"),
            ("/api/auth/verify", "GET")  # This should return 401 but server should respond
        ]

        endpoint_results = {}

        for endpoint, method in endpoints:
            try:
                start_time = time.time()
                if method == "GET":
                    response = requests.get(f"{API_URL}{endpoint}", timeout=5)
                response_time = time.time() - start_time

                endpoint_results[endpoint] = {
                    'status_code': response.status_code,
                    'response_time': response_time,
                    'success': response.status_code < 500  # Accept 4xx as "working"
                }

            except Exception as e:
                endpoint_results[endpoint] = {
                    'status_code': 0,
                    'response_time': 5.0,
                    'success': False,
                    'error': str(e)
                }

        return endpoint_results

    def test_database_connectivity(self):
        """Test database connectivity through API"""
        try:
            # Test user creation/login (tests MongoDB)
            test_user = f"monitor_test_{int(time.time())}"
            response = requests.post(f"{API_URL}/api/auth/login",
                                     json={"username": test_user}, timeout=5)

            return response.status_code == 200
        except:
            return False

    def check_system_resources(self):
        """Check system resource usage (if available)"""
        # This could be expanded to check Docker container stats
        # For now, we'll simulate based on response times

        stats = self.metrics.get_stats()
        if not stats:
            return "UNKNOWN"

        avg_response = stats['avg_response_time']
        if avg_response < 0.5:
            return "EXCELLENT"
        elif avg_response < 1.0:
            return "GOOD"
        elif avg_response < 2.0:
            return "FAIR"
        else:
            return "POOR"

    def send_alert(self, alert_type, message):
        """Send alert (log for now, could be extended to email/Slack)"""
        alert_key = f"{alert_type}_{message}"

        # Avoid duplicate alerts within 5 minutes
        current_time = time.time()
        if alert_key in self.alerts_sent:
            if current_time - self.alerts_sent[alert_key] < 300:  # 5 minutes
                return

        self.alerts_sent[alert_key] = current_time
        log(f"🚨 ALERT [{alert_type}]: {message}", Colors.RED + Colors.BOLD)

    def check_alerts(self, stats):
        """Check if any alerts should be triggered"""
        if not stats:
            return

        # Response time alert
        if stats['avg_response_time'] > ALERT_THRESHOLDS['response_time']:
            self.send_alert("PERFORMANCE",
                            f"High response time: {stats['avg_response_time']:.2f}s")

        # Error rate alert
        if stats['error_rate'] > ALERT_THRESHOLDS['error_rate']:
            self.send_alert("ERROR_RATE",
                            f"High error rate: {stats['error_rate']:.1f}%")

        # Success rate alert
        if stats['success_rate'] < ALERT_THRESHOLDS['success_rate']:
            self.send_alert("SUCCESS_RATE",
                            f"Low success rate: {stats['success_rate']:.1f}%")

    def print_dashboard(self):
        """Print monitoring dashboard"""
        # Clear screen (works on most terminals)
        print("\033[2J\033[H", end="")

        print(f"{Colors.BOLD}{Colors.CYAN}")
        print("╔══════════════════════════════════════════════════════════╗")
        print("║              SYSTEM HEALTH DASHBOARD                    ║")
        print("╚══════════════════════════════════════════════════════════╝")
        print(f"{Colors.END}\n")

        # Current status
        health_ok, response_time, health_data = self.check_api_health()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if health_ok:
            status_color = Colors.GREEN
            status_text = "🟢 HEALTHY"
        else:
            status_color = Colors.RED
            status_text = "🔴 UNHEALTHY"

        print(f"{Colors.BOLD}📊 Current Status: {status_color}{status_text}{Colors.END}")
        print(f"🕐 Last Check: {current_time}")
        print(f"⚡ Response Time: {response_time:.3f}s")
        print()

        # Performance metrics
        stats = self.metrics.get_stats()
        if stats:
            print(f"{Colors.BOLD}📈 Performance Metrics:{Colors.END}")
            print(f"   Avg Response: {stats['avg_response_time']:.3f}s")
            print(f"   Min Response: {stats['min_response_time']:.3f}s")
            print(f"   Max Response: {stats['max_response_time']:.3f}s")
            print(f"   Success Rate: {stats['success_rate']:.1f}%")
            print(f"   Error Rate: {stats['error_rate']:.1f}%")
            print(f"   Total Requests: {stats['total_requests']}")
            print(f"   Uptime: {str(stats['uptime']).split('.')[0]}")
            print()

        # Test additional endpoints
        endpoint_results = self.test_api_endpoints()
        print(f"{Colors.BOLD}🔗 Endpoint Health:{Colors.END}")
        for endpoint, result in endpoint_results.items():
            status = "✅" if result['success'] else "❌"
            print(f"   {status} {endpoint}: {result['status_code']} ({result['response_time']:.3f}s)")
        print()

        # Database connectivity
        db_ok = self.test_database_connectivity()
        db_status = "✅ Connected" if db_ok else "❌ Disconnected"
        print(f"{Colors.BOLD}🗄️ Database: {db_status}{Colors.END}")
        print()

        # System resources
        resource_status = self.check_system_resources()
        resource_colors = {
            "EXCELLENT": Colors.GREEN,
            "GOOD": Colors.GREEN,
            "FAIR": Colors.YELLOW,
            "POOR": Colors.RED,
            "UNKNOWN": Colors.BLUE
        }
        resource_color = resource_colors.get(resource_status, Colors.WHITE)
        print(f"{Colors.BOLD}💻 System Performance: {resource_color}{resource_status}{Colors.END}")
        print()

        # Error breakdown
        if self.metrics.error_types:
            print(f"{Colors.BOLD}❌ Error Breakdown:{Colors.END}")
            for error_type, count in self.metrics.error_types.items():
                print(f"   {error_type}: {count}")
            print()

        # Alerts status
        if stats:
            self.check_alerts(stats)

        print(f"{Colors.BOLD}🔧 Monitoring Configuration:{Colors.END}")
        print(f"   Check Interval: {MONITOR_INTERVAL}s")
        print(f"   Response Time Alert: >{ALERT_THRESHOLDS['response_time']}s")
        print(f"   Error Rate Alert: >{ALERT_THRESHOLDS['error_rate']}%")
        print(f"   Success Rate Alert: <{ALERT_THRESHOLDS['success_rate']}%")
        print()

        print(f"{Colors.BLUE}Press Ctrl+C to stop monitoring{Colors.END}")

    def run_continuous_monitoring(self):
        """Run continuous monitoring loop"""
        log("🚀 Starting continuous system monitoring...", Colors.GREEN + Colors.BOLD)
        log(f"📊 Monitoring interval: {MONITOR_INTERVAL} seconds", Colors.BLUE)

        self.monitoring = True

        try:
            while self.monitoring:
                self.print_dashboard()
                time.sleep(MONITOR_INTERVAL)

        except KeyboardInterrupt:
            log("\n⚠️ Monitoring stopped by user", Colors.YELLOW)
        except Exception as e:
            log(f"\n🚨 Monitoring error: {e}", Colors.RED)
        finally:
            self.monitoring = False

    def run_single_check(self):
        """Run a single comprehensive health check"""
        log("🔍 Running single health check...", Colors.CYAN)

        # Basic health check
        health_ok, response_time, health_data = self.check_api_health()

        if health_ok:
            log("✅ API Health: OK", Colors.GREEN)
            log(f"⚡ Response Time: {response_time:.3f}s", Colors.BLUE)
        else:
            log("❌ API Health: FAILED", Colors.RED)
            return False

        # Test endpoints
        endpoint_results = self.test_api_endpoints()
        working_endpoints = sum(1 for r in endpoint_results.values() if r['success'])
        total_endpoints = len(endpoint_results)

        log(f"🔗 Endpoints: {working_endpoints}/{total_endpoints} working",
            Colors.GREEN if working_endpoints == total_endpoints else Colors.YELLOW)

        # Test database
        db_ok = self.test_database_connectivity()
        log(f"🗄️ Database: {'Connected' if db_ok else 'Failed'}",
            Colors.GREEN if db_ok else Colors.RED)

        # Overall assessment
        if health_ok and working_endpoints >= total_endpoints * 0.8 and db_ok:
            log("🎉 Overall Status: HEALTHY", Colors.GREEN + Colors.BOLD)
            return True
        else:
            log("⚠️ Overall Status: ISSUES DETECTED", Colors.YELLOW + Colors.BOLD)
            return False


def main():
    """Main function"""
    import sys

    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔══════════════════════════════════════════════════════════╗")
    print("║            INTERVIEW ASSISTANT HEALTH MONITOR           ║")
    print("║                                                          ║")
    print("║  Monitors: API health, performance, database, errors     ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}\n")

    monitor = SystemHealthMonitor()

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        # Run single check
        success = monitor.run_single_check()
        sys.exit(0 if success else 1)
    else:
        # Run continuous monitoring
        monitor.run_continuous_monitoring()


if __name__ == "__main__":
    main()