# firmware_monitor.py

import time
import json
from collections import defaultdict
import sys
import io
from datetime import datetime, timezone
import os

# Prefer user's local timezone (San Jose) for the "local" stamp, with safe fallback
try:
    from zoneinfo import ZoneInfo
    _LOCAL_TZ = ZoneInfo("America/Los_Angeles")
except Exception:
    _LOCAL_TZ = None


# --- Configuration and Mock Data ---

# Original scenario (Low Load)
MOCK_LOG_DATA_LOW_LOAD = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "CPU Usage", "timestamp_ms": 1500, "metric": {"cpu_percent": 5.2, "mem_kbytes": 200, "power_mw": 15, "temperature_c": 35.5, "mode": "NORMAL"}},
    {"event": "Task Executed", "timestamp_ms": 1750, "metric": {"latency_us": 250, "cpu_percent": 6.1}},
    {"event": "CPU Usage", "timestamp_ms": 2500, "metric": {"cpu_percent": 4.8, "mem_kbytes": 205, "power_mw": 14, "temperature_c": 36.1, "mode": "NORMAL"}},
    {"event": "Peripheral Ready", "timestamp_ms": 3000, "metric": {"boot_status": "READY"}},
    {"event": "Task Executed", "timestamp_ms": 3100, "metric": {"latency_us": 150, "cpu_percent": 5.5}},
    {"event": "CPU Usage", "timestamp_ms": 3500, "metric": {"cpu_percent": 7.1, "mem_kbytes": 210, "power_mw": 18, "temperature_c": 37.0, "mode": "NORMAL"}},
    {"event": "Task Executed", "timestamp_ms": 3700, "metric": {"latency_us": 400, "cpu_percent": 8.5}},
    {"event": "System Idle", "timestamp_ms": 5000, "metric": {"boot_status": "COMPLETE"}},
]

# High Load scenario
MOCK_LOG_DATA_HIGH_LOAD = [
    {"event": "System Start", "timestamp_ms": 50, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "CPU Usage", "timestamp_ms": 1000, "metric": {"cpu_percent": 15.0, "mem_kbytes": 350, "power_mw": 35, "temperature_c": 45.0, "mode": "NORMAL"}},
    {"event": "Task Executed", "timestamp_ms": 1100, "metric": {"latency_us": 550, "cpu_percent": 18.2}},
    {"event": "Peripheral Ready", "timestamp_ms": 2100, "metric": {"boot_status": "READY"}},
    {"event": "CPU Usage", "timestamp_ms": 2500, "metric": {"cpu_percent": 22.1, "mem_kbytes": 380, "temperature_c": 50.0, "mode": "NORMAL"}},
    {"event": "Task Executed", "timestamp_ms": 2600, "metric": {"latency_us": 950, "cpu_percent": 25.5}},
]

# Security Breach Test
MOCK_LOG_DATA_SECURITY_BREACH = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT"}},
    {"event": "Authentication Failed", "timestamp_ms": 500, "metric": {"attempt_count": 1}},
    {"event": "CPU Usage", "timestamp_ms": 1000, "metric": {"cpu_percent": 5.0, "temperature_c": 30.0}},
    {"event": "Authentication Failed", "timestamp_ms": 1500, "metric": {"attempt_count": 2}},
    {"event": "Authentication Failed", "timestamp_ms": 1800, "metric": {"attempt_count": 3}},
    {"event": "SECURITY ALERT", "timestamp_ms": 2000, "metric": {"security_state": "BREACH_DETECTED"}},
    {"event": "Peripheral Ready", "timestamp_ms": 2500, "metric": {"boot_status": "READY"}},
]

# Boost Cycle Analysis Test
MOCK_LOG_DATA_BOOST_CYCLE = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL", "power_mw": 20}},
    {"event": "Request Boost", "timestamp_ms": 500},
    {"event": "CPU Usage", "timestamp_ms": 800, "metric": {"mode": "BOOST", "power_mw": 60, "latency_us": 50}},  # BOOST START (800ms)
    {"event": "Exit Boost", "timestamp_ms": 2000},
    {"event": "CPU Usage", "timestamp_ms": 2500, "metric": {"mode": "NORMAL", "power_mw": 25}},  # BOOST END (2000ms -> 1200ms duration)
    {"event": "Request Boost", "timestamp_ms": 3000},
    {"event": "CPU Usage", "timestamp_ms": 3200, "metric": {"mode": "BOOST", "power_mw": 55}},  # BOOST START 2 (3200ms)
    {"event": "Peripheral Ready", "timestamp_ms": 4000, "metric": {"boot_status": "READY", "mode": "BOOST"}},  # System ends in BOOST mode
]

# Secured Boost Activation Test
MOCK_LOG_DATA_SECURED_BOOST = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "Security Check Start", "timestamp_ms": 500},
    {"event": "Authentication Success", "timestamp_ms": 800, "metric": {"security_state": "SECURE", "auth_attempts": 0}},
    {"event": "Request Boost", "timestamp_ms": 900},
    {"event": "CPU Usage", "timestamp_ms": 1000, "metric": {"mode": "BOOST", "power_mw": 85, "temperature_c": 50.0}},  # BOOST START
    {"event": "Task Executed", "timestamp_ms": 1500, "metric": {"latency_us": 100, "cpu_percent": 35.0}},
    {"event": "CPU Usage", "timestamp_ms": 2000, "metric": {"mode": "BOOST", "power_mw": 90, "temperature_c": 55.0}},
    {"event": "Task Executed", "timestamp_ms": 2500, "metric": {"latency_us": 80, "cpu_percent": 40.0}},
    {"event": "Exit Boost", "timestamp_ms": 3000},
    {"event": "CPU Usage", "timestamp_ms": 3200, "metric": {"mode": "NORMAL", "power_mw": 25, "temperature_c": 40.0}},  # BOOST END
    {"event": "Peripheral Ready", "timestamp_ms": 4000, "metric": {"boot_status": "READY"}},
]

# Boost Denied (Security Lockout) Test
MOCK_LOG_DATA_BOOST_DENIED = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "Authentication Failed", "timestamp_ms": 500, "metric": {"attempt_count": 1}},
    {"event": "SECURITY ALERT", "timestamp_ms": 600, "metric": {"security_state": "BREACH_DETECTED"}},
    {"event": "Request Boost", "timestamp_ms": 1000},
    {"event": "CPU Usage", "timestamp_ms": 1500, "metric": {"mode": "NORMAL", "power_mw": 20, "temperature_c": 35.0}},  # System must remain in NORMAL
    {"event": "Task Executed", "timestamp_ms": 2000, "metric": {"latency_us": 500, "cpu_percent": 10.0}},
    {"event": "CPU Usage", "timestamp_ms": 2500, "metric": {"mode": "NORMAL", "power_mw": 22, "temperature_c": 36.0}},  # Still NORMAL
    {"event": "Peripheral Ready", "timestamp_ms": 3000, "metric": {"boot_status": "READY"}},
]

# Zero Log Data Test (Robustness Check)
MOCK_LOG_DATA_ZERO_DATA = []

# Mode Oscillation Stress Test
MOCK_LOG_DATA_MODE_OSCILLATION = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL", "power_mw": 20}},
    {"event": "Request Boost", "timestamp_ms": 500},
    {"event": "CPU Usage", "timestamp_ms": 600, "metric": {"mode": "BOOST", "power_mw": 80, "latency_us": 100}},
    {"event": "Exit Boost", "timestamp_ms": 700},
    {"event": "CPU Usage", "timestamp_ms": 800, "metric": {"mode": "NORMAL", "power_mw": 30, "latency_us": 500}},
    {"event": "Request Boost", "timestamp_ms": 900},
    {"event": "CPU Usage", "timestamp_ms": 1000, "metric": {"mode": "BOOST", "power_mw": 75, "latency_us": 150}},
    {"event": "Peripheral Ready", "timestamp_ms": 1500, "metric": {"boot_status": "READY", "mode": "BOOST"}},
]

# NEW SCENARIO: Power Dip/Intermittent Logging Test (Realistic Issue)
# Simulates a logging/communication failure mid-operation (3000ms to 6000ms gap).
MOCK_LOG_DATA_POWER_DIP = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL", "power_mw": 20}},
    {"event": "CPU Usage", "timestamp_ms": 1000, "metric": {"cpu_percent": 10.0, "power_mw": 25, "temperature_c": 38.0, "mode": "NORMAL"}},
    {"event": "Task Executed", "timestamp_ms": 2500, "metric": {"latency_us": 400, "cpu_percent": 15.0}},
    # --- Simulated data loss/dip from 3000ms to 6000ms ---
    {"event": "System Recovered", "timestamp_ms": 6500, "metric": {"cpu_percent": 5.0, "power_mw": 18, "temperature_c": 35.0, "mode": "NORMAL"}},
    {"event": "Task Executed", "timestamp_ms": 7000, "metric": {"latency_us": 100, "cpu_percent": 5.5}},
    {"event": "Peripheral Ready", "timestamp_ms": 7500, "metric": {"boot_status": "READY"}},
]

# NEW SCENARIO: Resource Contention Test (Realistic Peak Stress)
# Simulates a critical event where all primary metrics peak at the same time.
MOCK_LOG_DATA_RESOURCE_CONTENTION = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "CPU Usage", "timestamp_ms": 500, "metric": {"cpu_percent": 10.0, "power_mw": 25, "temperature_c": 38.0}},
    {"event": "Peripheral Ready", "timestamp_ms": 1500, "metric": {"boot_status": "READY"}},
    {"event": "Critical Task Start", "timestamp_ms": 2000},
    {"event": "CPU Usage", "timestamp_ms": 2050, "metric": {"mode": "BOOST", "cpu_percent": 95.0, "mem_kbytes": 950, "power_mw": 150, "temperature_c": 99.0}},  # ALL PEAKS HERE
    {"event": "Task Executed", "timestamp_ms": 2060, "metric": {"latency_us": 7500, "cpu_percent": 90.0}},  # Max Latency
    {"event": "CPU Usage", "timestamp_ms": 3500, "metric": {"mode": "NORMAL", "cpu_percent": 8.0, "mem_kbytes": 300, "power_mw": 20, "temperature_c": 45.0}},  # Recovery
]

# Other existing scenarios (updated with default mode if needed)
MOCK_LOG_DATA_SINGLE_POINT = [
    {"event": "System Start", "timestamp_ms": 50, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "Peripheral Ready", "timestamp_ms": 550, "metric": {"boot_status": "READY"}},
    {"event": "CPU Usage", "timestamp_ms": 600, "metric": {"cpu_percent": 5.0, "temperature_c": 30.0}},
]

MOCK_LOG_DATA_SPARSE = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "Peripheral Ready", "timestamp_ms": 1000, "metric": {"boot_status": "READY"}},
    {"event": "CPU Usage", "timestamp_ms": 3500, "metric": {"cpu_percent": 10.5, "mem_kbytes": 250, "temperature_c": 38.0}},
]

MOCK_LOG_DATA_SPIKE = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "CPU Usage", "timestamp_ms": 1000, "metric": {"cpu_percent": 8.0, "power_mw": 20, "temperature_c": 40.0}},
    {"event": "Peripheral Ready", "timestamp_ms": 1500, "metric": {"boot_status": "READY"}},
    {"event": "CPU Usage", "timestamp_ms": 2000, "metric": {"cpu_percent": 55.0, "power_mw": 80, "temperature_c": 85.0}},  # PEAK Load, PEAK Temp
]

MOCK_LOG_DATA_MISSING_TS = [
    {"event": "System Start", "timestamp_ms": 50, "metric": {"boot_status": "INIT"}},
    {"event": "CPU Usage", "metric": {"cpu_percent": 10.0, "mem_kbytes": 300, "power_mw": 30, "temperature_c": 42.0}},
    {"event": "Peripheral Ready", "timestamp_ms": 1000, "metric": {"boot_status": "READY"}},
]

MOCK_LOG_DATA_EXTREME_LATENCY = [
    {"event": "System Start", "timestamp_ms": 10, "metric": {"boot_status": "INIT"}},
    *[
        {"event": f"Task Executed {i}", "timestamp_ms": 1000 + i, "metric": {"latency_us": 100}}
        for i in range(20)
    ],
    {"event": "Task Executed (OUTLIER)", "timestamp_ms": 10000, "metric": {"latency_us": 5000}},
    {"event": "Peripheral Ready", "timestamp_ms": 15000, "metric": {"boot_status": "READY"}},
]

MOCK_LOG_DATA_THERMAL_SPIKE = [
    {"event": "System Start", "timestamp_ms": 100, "metric": {"boot_status": "INIT", "mode": "NORMAL"}},
    {"event": "CPU Usage", "timestamp_ms": 2500, "metric": {"cpu_percent": 60.0, "power_mw": 90, "temperature_c": 95.0}},  # Thermal Alert - Peak
    {"event": "Peripheral Ready", "timestamp_ms": 4000, "metric": {"boot_status": "READY"}},
]


class FirmwarePerformanceAnalyzer:
    """
    Analyzes log data collected from embedded firmware to calculate key performance metrics.
    """

    def __init__(self, log_data):
        """Initializes the analyzer with log data."""
        if not isinstance(log_data, list):
            raise ValueError("Log data must be provided as a list of dictionaries.")
        self.log_data = log_data

    def get_metrics_by_type(self, metric_key):
        """
        Extracts all numeric values for a specific metric (e.g., 'cpu_percent') from the logs.
        Handles cases where the metric might be missing or non-numeric.
        """
        values = []
        for entry in self.log_data:
            metric = entry.get("metric", {})
            value = metric.get(metric_key)
            if isinstance(value, (int, float)):
                values.append(value)
        return values

    def _calculate_statistics(self, readings):
        """Helper to safely calculate statistics from a list of readings."""
        if not readings:
            return None
        return {
            "Average": sum(readings) / len(readings),
            "Peak": max(readings),
            "Min": min(readings)
        }

    # --- Core Analysis Functions ---
    def calculate_boot_time(self):
        """
        Calculates the time taken from System Start (INIT) to System Ready (READY).
        """
        start_time = None
        ready_time = None

        for entry in self.log_data:
            metric = entry.get("metric", {})
            try:
                timestamp = entry["timestamp_ms"]
                if not isinstance(timestamp, (int, float)):
                    continue
                if metric.get("boot_status") == "INIT":
                    start_time = timestamp
                elif metric.get("boot_status") == "READY":
                    ready_time = timestamp
                    break
            except KeyError:
                continue

        if start_time is not None and ready_time is not None and ready_time > start_time:
            # Convert ms to seconds
            boot_time_s = (ready_time - start_time) / 1000.0
            return boot_time_s
        return "N/A (Could not find valid start and ready markers)"

    def analyze_security_events(self):
        """Calculates security metrics like failed authentication attempts and breach flags."""
        failed_attempts = 0
        security_breaches = 0
        for entry in self.log_data:
            metric = entry.get("metric", {})
            # Count failed authentication attempts
            if entry.get("event") == "Authentication Failed":
                failed_attempts += 1
            # Count explicit security breaches
            if metric.get("security_state") == "BREACH_DETECTED":
                security_breaches += 1

        results = {}
        if failed_attempts > 0:
            results["Failed Auth Attempts"] = failed_attempts
        if security_breaches > 0:
            results["Security Breach Detections"] = security_breaches
        return results if results else None

    def analyze_boost_cycle_time(self):
        """Calculates the total time spent in 'BOOST' mode."""
        boost_start_time = None
        total_boost_duration = 0

        for entry in self.log_data:
            try:
                timestamp = entry["timestamp_ms"]
                metric = entry.get("metric", {})
                current_mode = metric.get("mode")

                # Check for transition into BOOST mode
                if current_mode == "BOOST" and boost_start_time is None:
                    index = self.log_data.index(entry)
                    prev_mode = self.log_data[index - 1].get("metric", {}).get("mode") if index > 0 else "N/A"
                    if prev_mode != "BOOST":
                        boost_start_time = timestamp

                # Check for transition out of BOOST mode
                elif current_mode != "BOOST" and boost_start_time is not None:
                    total_boost_duration += (timestamp - boost_start_time)
                    boost_start_time = None

            except KeyError:
                continue  # Skip entries without timestamp

        # If the log ends while still in BOOST mode, account for time until the last log entry
        if boost_start_time is not None and self.log_data:
            last_timestamp = self.log_data[-1].get("timestamp_ms", 0)
            if last_timestamp > boost_start_time:
                total_boost_duration += (last_timestamp - boost_start_time)

        if total_boost_duration > 0:
            # Convert ms to seconds
            return total_boost_duration / 1000.0
        return None

    def analyze_metrics(self):
        """
        Performs statistical analysis on CPU, Memory, Power, Temperature, and Latency metrics.
        """
        results = {}

        # 1. Standard Metrics
        cpu_readings = self.get_metrics_by_type("cpu_percent")
        if (cpu_stats := self._calculate_statistics(cpu_readings)):
            results["CPU Usage (%)"] = cpu_stats

        mem_readings = self.get_metrics_by_type("mem_kbytes")
        if (mem_stats := self._calculate_statistics(mem_readings)):
            results["Memory Footprint (KB)"] = mem_stats

        power_readings = self.get_metrics_by_type("power_mw")
        if (power_stats := self._calculate_statistics(power_readings)):
            results["Power Consumption (mW)"] = power_stats

        temp_readings = self.get_metrics_by_type("temperature_c")
        if (temp_stats := self._calculate_statistics(temp_readings)):
            results["Temperature (C)"] = temp_stats

        # 2. Task Latency Analysis (with P95)
        latency_readings = self.get_metrics_by_type("latency_us")
        if latency_readings:
            latency_readings.sort()
            N = len(latency_readings)
            p95_index = int(N * 0.95)
            p95_value = latency_readings[min(p95_index, N - 1)]
            results["Task Latency (us)"] = {
                "Average": sum(latency_readings) / N,
                "Peak (Max)": latency_readings[-1],
                "P95 Latency": p95_value,
                "Min": latency_readings[0]
            }

        return results

    def run_analysis(self, scenario_name="Default"):
        """
        Executes all analysis tasks and formats the output.
        (Output is printed, which is later captured by run_all_tests)
        """
        # Scenario Header
        print("\n" + "=" * 60)
        print(f"Firmware Performance Analysis Report: {scenario_name}")
        print("=" * 60)

        # A. Boot Time Analysis (Simple Metric)
        boot_time = self.calculate_boot_time()
        print(f"BOOT_TIME_METRIC\nBoot Time\n{boot_time} seconds")
        print("-" * 60)

        # B. Security Analysis
        security_results = self.analyze_security_events()
        if security_results:
            print("\n--- Security Analysis ---")
            for key, value in security_results.items():
                print(f"SECURITY_METRIC\n{key}\n{value}")
            print("-" * 60)

        # C. Boost Mode Analysis
        boost_duration = self.analyze_boost_cycle_time()
        if boost_duration is not None:
            print("\n--- Performance Mode Analysis ---")
            print(f"BOOST_METRIC\nTotal Boost Mode Duration\n{boost_duration:.2f} seconds")
            print("-" * 60)

        # D. Detailed Metric Analysis
        metric_results = self.analyze_metrics()
        if not metric_results:
            print("No valid metrics found for detailed analysis.")
            print("-" * 60)
            return

        for metric_name, data in metric_results.items():
            print(f"\n--- {metric_name} ---")
            for key, value in data.items():
                formatted_value = f"{value:.2f}" if isinstance(value, (int, float)) else str(value)
                # Use a specific prefix for easy HTML parsing
                print(f"DETAIL_METRIC\n{key} ({metric_name.split('(')[0].strip()})\n{formatted_value}")
        print("\n" + "-" * 60)


def _text_to_html(text_report):
    """
    Converts the plain text report into a compact, structured HTML document.
    """
    author_line = ""
    run_info_lines = []  # NEW: collect run date/time lines for header
    scenario_html_sections = []
    summary_html_sections = []

    # State variables
    in_summary_mode = False
    in_test_results_grid = False
    in_scenario_card = False
    in_metric_group = False

    # 1. Find Author + Run Date/Time lines (collect both)
    for line in text_report.splitlines():
        if line.startswith("Author:"):
            author_line = f'<p class="author-info">{line.strip()}</p>'
        elif line.startswith("Run Date/Time"):
            run_info_lines.append(f'<p class="run-info">{line.strip()}</p>')

    # 2. Process lines to create structured HTML components
    for line in text_report.splitlines():
        line = line.strip()

        # --- State transitions and closing tags ---
        # Transition out of the Final Test Results Grid
        if in_test_results_grid and not line.startswith("\n "):
            summary_html_sections.append('</div>')  # Close the test result grid wrapper
            in_test_results_grid = False

        # Start of a new scenario
        if line.startswith("Firmware Performance Analysis Report:"):
            # Close previous blocks if they were open
            if in_metric_group:
                scenario_html_sections.append('</div>')  # Close hanging metric group
            if in_scenario_card:
                scenario_html_sections.append('</div>')  # Close previous scenario card

            scenario_name = line.split(":", 1)[1].strip()
            scenario_html_sections.append(f'<div class="scenario-card">')
            scenario_html_sections.append(f'<h3>{scenario_name}</h3>')
            in_scenario_card = True
            in_metric_group = False  # Reset metric group state
            in_summary_mode = False

        # Start of summary
        elif line.startswith("FINAL TEST SUMMARY REPORT"):
            # Close previous blocks
            if in_metric_group:
                scenario_html_sections.append('</div>')
            if in_scenario_card:
                scenario_html_sections.append('</div>')
            in_metric_group = False
            in_scenario_card = False
            in_summary_mode = True
            summary_html_sections.append('<div class="summary-card full-span"><h2>Final Test Summary</h2>')

        # --- Content Generation (Inside Scenario Card) ---
        elif in_scenario_card:
            if line.startswith("--- "):
                # Sub-headers like "--- Security Analysis ---" or "--- CPU Usage (%) ---"
                if in_metric_group:
                    scenario_html_sections.append('</div>')  # Close previous metric group
                header_text = line.strip("- ").strip()
                scenario_html_sections.append(f'<h4>{header_text}</h4>')
                scenario_html_sections.append(f'<div class="metric-group">')
                in_metric_group = True

            elif line.startswith("BOOT_TIME_METRIC\n"):
                # Simple Boot Metric (outside a group)
                if in_metric_group:
                    scenario_html_sections.append('</div>')
                in_metric_group = False
                try:
                    _, key, value = line.split("\n", 2)
                    scenario_html_sections.append(f'<h4>Boot Analysis</h4>')
                    scenario_html_sections.append(f'<div class="metric-item single-metric">')
                    scenario_html_sections.append(f' <span class="metric-key">{key}:</span>')
                    scenario_html_sections.append(f' <span class="metric-value">{value}</span>')
                    scenario_html_sections.append(f'</div>')
                except ValueError:
                    pass

            elif in_metric_group and (
                line.startswith("SECURITY_METRIC\n")
                or line.startswith("BOOST_METRIC\n")
                or line.startswith("DETAIL_METRIC\n")
            ):
                try:
                    _, key, value = line.split("\n", 2)
                    scenario_html_sections.append(f'<div class="metric-item">')
                    scenario_html_sections.append(f' <span class="metric-key">{key}:</span>')
                    scenario_html_sections.append(f' <span class="metric-value">{value}</span>')
                    scenario_html_sections.append(f'</div>')
                except ValueError:
                    pass  # Skip malformed lines

        # --- Content Generation (Inside Summary Card) ---
        elif in_summary_mode:
            # Overall summary metrics (Total, Passed, Failed, Time)
            if (
                line.startswith("Total Tests Executed:")
                or line.startswith("Tests Passed:")
                or line.startswith("Tests Failed:")
                or line.startswith("Total Execution Time:")
            ):
                key, value = line.split(":", 1)
                value_class = "summary-value time" if "Execution Time" in key else "summary-value"
                summary_html_sections.append(
                    f'<div class="summary-item"><span class="summary-key">{key}:</span>'
                    f'<span class="{value_class}">{value.strip()}</span></div>'
                )

            # Individual test status line (grid)
            elif ":" in line and not line.startswith("=") and not line.startswith("-"):
                if not in_test_results_grid:
                    summary_html_sections.append('<h4>Individual Test Status:</h4>')
                    summary_html_sections.append('<div class="test-result-grid">')
                    in_test_results_grid = True
                parts = line.split(":", 1)
                if len(parts) == 2:
                    name, status = parts
                    status_class = "pass" if "PASS" in status else "fail"
                    summary_html_sections.append(
                        f'<div class="test-result {status_class}"><span class="test-name">{name.strip()}</span>'
                        f'<span class="test-status">{status.strip()}</span></div>'
                    )

    # Final closure checks
    if in_metric_group:
        scenario_html_sections.append('</div>')  # Close the last metric group
    if in_test_results_grid:
        summary_html_sections.append('</div>')  # Close the test result grid wrapper
    if in_scenario_card:
        scenario_html_sections.append('</div>')  # Close the last scenario card
    if in_summary_mode:
        summary_html_sections.append('</div>')  # Close the summary card

    scenario_html = "".join(scenario_html_sections)
    summary_html = "".join(summary_html_sections)
    run_info_html = "".join(run_info_lines)

    # Compile the final HTML structure with separate containers
    html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compact Firmware Analysis Report</title>
    <style>
    body {{
        font-family: 'Inter', sans-serif;
        background-color: #f0f4f8;
        color: #1a202c;
        padding: 20px;
        margin: 0;
        line-height: 1.5;
    }}
    .container {{
        max-width: 1200px;
        margin: 0 auto;
        background-color: #ffffff;
        padding: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-radius: 12px;
    }}
    h1 {{
        color: #1d4ed8;
        border-bottom: 3px solid #bfdbfe;
        padding-bottom: 10px;
        margin-bottom: 20px;
        font-size: 2em;
    }}
    .author-info {{
        color: #4b5563;
        font-size: 0.9em;
        margin-bottom: 6px;
    }}
    /* NEW: style for run date/time rows */
    .run-info {{
        color: #4b5563;
        font-size: 0.9em;
        margin: 0 0 6px 0;
    }}

    /* --- GRID LAYOUT FOR SCENARIO CARDS --- */
    .report-grid {{
        display: grid;
        grid-template-columns: 1fr; /* Default: Single column for mobile */
        gap: 20px;
        margin-top: 15px;
    }}
    @media (min-width: 768px) {{
        .report-grid {{
            grid-template-columns: 1fr 1fr; /* Two columns on tablet/desktop */
        }}
    }}
    .scenario-card {{
        background-color: #f9fafb;
        border: 1px solid #e5e7eb;
        padding: 15px;
        margin-bottom: 0;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }}
    .scenario-card h3 {{
        color: #059669;
        font-size: 1.4em;
        margin-top: 0;
        margin-bottom: 10px;
        border-bottom: 2px solid #a7f3d0;
        padding-bottom: 5px;
    }}
    .scenario-card h4 {{
        color: #3b82f6;
        font-size: 1.1em;
        margin-top: 15px;
        margin-bottom: 8px;
        font-weight: 600;
    }}

    /* --- NEW GRID FOR SCENARIO METRIC GROUPS (2-3 COLUMNS) --- */
    .metric-group {{
        display: grid;
        grid-template-columns: 1fr; /* Mobile: 1 column */
        gap: 10px;
        margin-bottom: 15px;
    }}
    @media (min-width: 640px) {{
        .metric-group {{
            grid-template-columns: 1fr 1fr; /* Tablet/Medium: 2 columns */
        }}
    }}
    @media (min-width: 1024px) {{
        .metric-group {{
            grid-template-columns: 1fr 1fr 1fr; /* Desktop: 3 columns */
        }}
    }}
    .metric-item {{
        display: flex;
        justify-content: space-between;
        background-color: #ffffff;
        padding: 8px 12px;
        border-radius: 6px;
        border-left: 4px solid #fcd34d;
        font-size: 0.9em;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
    }}
    /* Specific styling for the single boot metric to stand out slightly */
    .metric-item.single-metric {{
        border-left: 4px solid #34d399; /* Green border for boot time */
    }}
    .metric-key {{
        color: #4b5563;
        font-weight: 500;
    }}
    .metric-value {{
        color: #1f2937;
        font-weight: 700;
    }}

    /* Summary Card Styling */
    .summary-card {{
        background-color: #dbeafe;
        border: 2px solid #93c5fd;
        padding: 20px;
        margin-top: 30px;
        border-radius: 10px;
    }}
    .summary-card h2 {{
        color: #1e3a8a;
        font-size: 1.8em;
        margin-top: 0;
        margin-bottom: 15px;
        text-align: center;
    }}
    .summary-item {{
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        border-bottom: 1px dotted #93c5fd;
    }}
    .summary-key {{ font-weight: 600; color: #1f2937; }}
    .summary-value {{ font-weight: 700; color: #10b981; }}
    .summary-value.time {{ font-weight: 700; color: #f97316; }} /* Orange for time */

    /* --- GRID FOR FINAL TEST RESULTS (2-3 COLUMNS) --- */
    .test-result-grid {{
        display: grid;
        grid-template-columns: repeat(2, 1fr); /* Tablet/Default: 2 columns */
        gap: 10px;
        margin-top: 15px;
    }}
    @media (min-width: 1024px) {{
        .test-result-grid {{
            grid-template-columns: repeat(3, 1fr); /* Desktop: 3 columns */
        }}
    }}
    @media (max-width: 640px) {{
        .test-result-grid {{
            grid-template-columns: 1fr; /* Mobile: 1 column */
        }}
    }}
    .test-result {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 10px;
        border-radius: 6px;
        font-size: 0.85em;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        min-width: 150px;
    }}
    .test-name {{
        margin-right: 10px;
        overflow-wrap: break-word;
        word-break: break-word;
    }}
    .test-status {{
        font-weight: 700;
        flex-shrink: 0;
    }}
    .test-result.pass {{ background-color: #d1fae5; border-left: 3px solid #10b981; }}
    .test-result.fail {{ background-color: #fee2e2; border-left: 3px solid #ef4444; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Firmware Performance Analysis Comprehensive Report</h1>
        {author_line}
        {run_info_html}
        <!-- Scenario Cards Grid -->
        <div class="report-grid">
        {scenario_html}
        </div>
        <!-- Final Summary Card (contains the test-result-grid) -->
        {summary_html}
    </div>
</body>
</html>"""
    return html_output


def run_all_tests():
    """
    Executes all defined tests, captures the output, and writes it to timestamped .txt and .html files
    in the 'reports/' directory.
    """
    # --- Start timing the entire test run ---
    start_time = time.time()

    # 1. Prepare for output capture
    old_stdout = sys.stdout
    redirected_output = io.StringIO()
    sys.stdout = redirected_output  # Redirect all print statements to the in-memory buffer

    # --- Add Author Information + Run Date/Time to the Start of the TXT Report ---
    print("\n" + "=" * 60)
    print("Author: Bang Thien Nguyen ontario1998@gmail.com")
    print("=" * 60)
    # NEW: Emit run date/time (local + UTC) so it appears in .txt and gets parsed into HTML
    try:
        if _LOCAL_TZ is not None:
            run_local_dt = datetime.now(_LOCAL_TZ)
        else:
            run_local_dt = datetime.now().astimezone()
    except Exception:
        run_local_dt = datetime.now().astimezone()
    run_local = run_local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    run_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"Run Date/Time (local): {run_local}")
    print(f"Run Date/Time (UTC):   {run_utc}")

    test_results = []

    # 1. Define all tests
    metric_tests = [
        ("Low Load Test", MOCK_LOG_DATA_LOW_LOAD),
        ("High Load Test (Robustness Check)", MOCK_LOG_DATA_HIGH_LOAD),
        ("Single Data Point Test", MOCK_LOG_DATA_SINGLE_POINT),
        ("Sparse Data Test", MOCK_LOG_DATA_SPARSE),
        ("Stress Spike & Recovery Test", MOCK_LOG_DATA_SPIKE),
        ("Missing Timestamp Robustness Test", MOCK_LOG_DATA_MISSING_TS),
        ("Extreme Latency Test (P95 vs Peak)", MOCK_LOG_DATA_EXTREME_LATENCY),
        ("Thermal Spike Test", MOCK_LOG_DATA_THERMAL_SPIKE),
        ("Security Breach Test", MOCK_LOG_DATA_SECURITY_BREACH),
        ("Boost Cycle Analysis Test", MOCK_LOG_DATA_BOOST_CYCLE),
        ("Secured Boost Activation Test", MOCK_LOG_DATA_SECURED_BOOST),
        ("Boost Denied (Security Lockout) Test", MOCK_LOG_DATA_BOOST_DENIED),
        ("Zero Log Data Test (Robustness Check)", MOCK_LOG_DATA_ZERO_DATA),
        ("Mode Oscillation Stress Test", MOCK_LOG_DATA_MODE_OSCILLATION),
        ("Power Dip/Intermittent Logging Test", MOCK_LOG_DATA_POWER_DIP),
        ("Resource Contention Test (Max Load)", MOCK_LOG_DATA_RESOURCE_CONTENTION),
    ]

    print("\nSimulating data collection from firmware logs...")
    time.sleep(0.01)

    # Execute all metric analysis tests
    for name, data in metric_tests:
        try:
            analyzer = FirmwarePerformanceAnalyzer(data)
            analyzer.run_analysis(scenario_name=name)
            test_results.append({"name": name, "status": "PASS"})
        except Exception as e:
            # Catches critical failures in the analysis logic for a given data set.
            print(f"Error in {name}: {e}", file=sys.stderr)
            print(f"CRITICAL_FAILURE\n{name}\n{e}")
            test_results.append({"name": name, "status": "FAIL (Critical Analysis Error)"})

    # 2. Robustness Test for Invalid Data Type (Pass if ValueError is caught)
    name = "Invalid Data Type Test (Robustness Check)"
    print("\nSimulating analysis with invalid data type for ValueError check...")
    try:
        FirmwarePerformanceAnalyzer("this is not a list")
        # If we reach here, the ValueError was NOT raised, which is a test failure.
        print(f"\n FAIL: Expected ValueError but initialization succeeded.")
        test_results.append({"name": name, "status": "FAIL (ValueError not raised)"})
    except ValueError as e:
        print(f"\n Successfully caught expected Error: {e}")
        test_results.append({"name": name, "status": "PASS (Caught expected error)"})
    except Exception as e:
        print(f"\n FAIL: Caught unexpected error: {e}")
        test_results.append({"name": name, "status": "FAIL (Wrong Error Caught)"})

    # 3. Print Final Summary (to buffer)
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if "PASS" in result["status"])
    failed_tests = total_tests - passed_tests

    # --- End timing and calculate duration ---
    end_time = time.time()
    execution_time_s = end_time - start_time

    # Print the final summary, including the new execution time
    print("\n" + "=" * 60)
    print(" FINAL TEST SUMMARY REPORT")
    print("-" * 60)
    print(f"Total Tests Executed: {total_tests}")
    print(f"Tests Passed: {passed_tests}")
    print(f"Tests Failed: {failed_tests}")
    print(f"Total Execution Time: {execution_time_s:.4f} seconds")
    print("-" * 60)
    for result in test_results:
        status_display = result['status']
        print(f"{result['name']:<40} : {status_display}")
    print("=" * 60)

    # 4. Restore stdout and process captured output
    sys.stdout = old_stdout
    text_report = redirected_output.getvalue()

    # --- Directory and File Path Setup ---
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)  # Ensure the reports directory exists

    # Get timestamp for file naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    txt_filename = os.path.join(report_dir, f"firmware_analysis_report_{timestamp}.txt")
    html_filename = os.path.join(report_dir, f"firmware_analysis_report_{timestamp}.html")

    # Write TXT file
    try:
        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(text_report)
    except Exception as e:
        print(f"ERROR: Could not write TXT file {txt_filename}: {e}")

    # Write HTML file
    try:
        html_content = _text_to_html(text_report)
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
    except Exception as e:
        print(f"ERROR: Could not write HTML file {html_filename}: {e}")

    # 5. Print the confirmation and file names clearly to the actual console (stdout)
    print("\n" + "=" * 60)
    print("--- GENERATING REPORT FILES COMPLETE ---")
    print(f"Full Analysis Report Content: See log file.")
    print(f"\nTXT Report File Generated: {txt_filename}")
    print(f"HTML Report File Generated: {html_filename}")
    print(f"Run completed: {run_local} / {run_utc}")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
