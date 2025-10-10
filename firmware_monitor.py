#!/usr/bin/env python3
"""
Firmware Performance Monitor & Report Generator
------------------------------------------------
Generates detailed firmware performance analysis reports
in both TXT and HTML formats with scenario-based metrics.

Changes in this version:
- Robust navigation using absolute URLs suitable for GitHub Pages project sites.
- SITE_BASE_PATH env var to override the base path (defaults to '/firmware_monitor/').
"""

import os
import sys
import datetime

# -------------------- CONFIGURATION --------------------
# Thresholds for evaluation (fixed values)
THRESHOLDS = {
    "CPU (%)": 80.0,
    "Memory (KB)": 900.0,
    "Boot Timestamps": 5000.0,
    "Power (mW)": 100.0,
    "Temperature (°C)": 85.0,
    "Latency (us)": 5000.0,
}

# Status color mapping
STATUS_COLORS = {
    "PASS": "#10b981",  # green
    "FAIL": "#ef4444",  # red
    "SKIP": "#6b7280",  # gray
    "MIXED": "#f59e0b"  # amber
}

# GitHub Pages project base path (absolute URL path).
# Example for repo "firmware_monitor": "/firmware_monitor/"
SITE_BASE_PATH = os.environ.get("SITE_BASE_PATH", "/firmware_monitor/")
if not SITE_BASE_PATH.startswith("/"):
    SITE_BASE_PATH = "/" + SITE_BASE_PATH
if not SITE_BASE_PATH.endswith("/"):
    SITE_BASE_PATH += "/"

LATEST_URL = SITE_BASE_PATH  # e.g., "/firmware_monitor/"
HISTORY_URL = SITE_BASE_PATH + "report_history/"

# -------------------- DATASET: FIXED DUMMY DATA --------------------
MOCK_LOG_DATA = [
    {
        "scenario": "Low Load Boot",
        "metrics": {
            "Boot Timestamps": {"min": 100, "max": 3000, "avg": 1550},
            "CPU (%)": {"min": 4.8, "max": 6.1, "avg": 5.37},
            "Memory (KB)": {"min": 200, "max": 205, "avg": 202.5},
            "Power (mW)": {"min": 14, "max": 15, "avg": 14.5},
            "Temperature (°C)": {"min": 35.5, "max": 36.1, "avg": 35.8},
            "Latency (us)": {"min": 250, "max": 250, "avg": 250},
        }
    },
    {
        "scenario": "High Load Boot",
        "metrics": {
            "Boot Timestamps": {"min": 50, "max": 2100, "avg": 1075},
            "CPU (%)": {"min": 15.0, "max": 25.5, "avg": 20.2},
            "Memory (KB)": {"min": 350, "max": 380, "avg": 365},
            "Power (mW)": {"min": 35, "max": 35, "avg": 35},
            "Temperature (°C)": {"min": 45.0, "max": 50.0, "avg": 47.5},
            "Latency (us)": {"min": 550, "max": 950, "avg": 750},
        }
    },
    {
        "scenario": "Power Dip",
        "metrics": {
            "Power (mW)": {"min": 18, "max": 25, "avg": 21},
            "Boot Timestamps": {"min": 100, "max": 7500, "avg": 3800},
            "CPU (%)": {"min": 5.0, "max": 15.0, "avg": 10},
            # Memory (KB) is missing -> Auto SKIP
            "Temperature (°C)": {"min": 35.0, "max": 38.0, "avg": 36.5},
            "Latency (us)": {"min": 400, "max": 400, "avg": 400},
        }
    },
    {
        "scenario": "Resource Contention",
        "metrics": {
            "Boot Timestamps": {"min": 100, "max": 4500, "avg": 2300},
            "CPU (%)": {"min": 8.0, "max": 95.0, "avg": 50.75},
            "Power (mW)": {"min": 20, "max": 150, "avg": 65},
            "Temperature (°C)": {"min": 38.0, "max": 99.0, "avg": 60.67},
            "Memory (KB)": {"min": 300, "max": 950, "avg": 625},
            "Latency (us)": {"min": 7500, "max": 7500, "avg": 7500},
        }
    },
    {
        "scenario": "Thermal Stress",
        "metrics": {
            "Boot Timestamps": {"min": 500, "max": 7000, "avg": 4000},
            "CPU (%)": {"min": 10, "max": 90, "avg": 60},
            "Memory (KB)": {"min": 600, "max": 950, "avg": 800},
            "Power (mW)": {"min": 50, "max": 120, "avg": 90},
            "Temperature (°C)": {"min": 60, "max": 100, "avg": 90},
            "Latency (us)": {"min": 1000, "max": 6000, "avg": 4000},
        }
    },
    {
        "scenario": "Recovery",
        "metrics": {
            "Boot Timestamps": {"min": 100, "max": 5000, "avg": 3000},
            "CPU (%)": {"min": 2, "max": 15, "avg": 8},
            # Memory (KB) missing -> auto SKIP
            "Power (mW)": {"min": 15, "max": 40, "avg": 20},
            "Temperature (°C)": {"min": 30, "max": 40, "avg": 35},
            "Latency (us)": {"min": 500, "max": 2000, "avg": 1200},
        }
    }
]

# -------------------- EVALUATION FUNCTIONS --------------------
def evaluate_metric(metric_name, values, thresholds):
    if not values or "avg" not in values:
        return "SKIP"
    avg_val = values["avg"]
    if metric_name in thresholds:
        return "PASS" if avg_val <= thresholds[metric_name] else "FAIL"
    return "SKIP"


def evaluate_scenario(scenario_data, thresholds):
    results = {}
    found_fail, found_pass, found_skip = False, False, False

    # Iterate over all defined metrics to find missing ones
    for metric_name in thresholds.keys():
        if metric_name in scenario_data["metrics"]:
            values = scenario_data["metrics"][metric_name]
            status = evaluate_metric(metric_name, values, thresholds)
        else:
            status = "SKIP"
        results[metric_name] = status

        if status == "FAIL":
            found_fail = True
        elif status == "PASS":
            found_pass = True
        elif status == "SKIP":
            found_skip = True

    if found_fail:
        scenario_status = "FAIL"
    elif found_pass and not found_fail and found_skip:
        scenario_status = "MIXED"
    elif found_pass and not found_fail:
        scenario_status = "PASS"
    else:
        scenario_status = "SKIP"

    return results, scenario_status


def render_status_label(status):
    color = STATUS_COLORS.get(status, "#000000")
    return f'<span style="color:{color}; font-weight:bold;">{status}</span>'


# -------------------- REPORT GENERATION --------------------
class FirmwarePerformanceAnalyzer:
    def __init__(self, build_number=None):
        self.build_number = build_number if build_number else "NA"
        self.scenarios = MOCK_LOG_DATA
        self.results = []

    def analyze(self):
        for scenario in self.scenarios:
            metrics_status, scenario_status = evaluate_scenario(scenario, THRESHOLDS)
            self.results.append({
                "scenario": scenario["scenario"],
                "metrics": scenario["metrics"],
                "metric_status": metrics_status,
                "scenario_status": scenario_status
            })

    def generate_reports(self):
        report_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(report_dir, exist_ok=True)

        # Local time in a simple timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"firmware_analysis_report_{timestamp}"
        if self.build_number != "NA":
            base_filename += f"_{self.build_number}"

        txt_path = os.path.join(report_dir, base_filename + ".txt")
        html_path = os.path.join(report_dir, base_filename + ".html")

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.generate_text_report(timestamp))

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.generate_html_report(timestamp))

        print(f"Reports generated:\n- {txt_path}\n- {html_path}")

    def generate_text_report(self, timestamp):
        lines = []
        lines.append("Firmware Performance Analysis Report")
        lines.append(f"Author: Bang Thien Nguyen ontario1998@gmail.com")
        lines.append(f"Build Number: {self.build_number}")
        lines.append(f"Test Run Timestamp: {timestamp}")
        lines.append("=" * 60)

        for result in self.results:
            lines.append(f"\nScenario: {result['scenario']}")
            # Iterate over all possible metrics from the status report
            for metric, status in sorted(result["metric_status"].items()):
                values = result["metrics"].get(metric)
                if values:
                    lines.append(
                        f" {metric}: Min={values['min']} "
                        f"Max={values['max']} "
                        f"Avg={values['avg']} -> {status}"
                    )
                else:
                    lines.append(f" {metric}: Not available -> {status}")

            lines.append(f"Scenario Status: {result['scenario_status']}")
            lines.append("-" * 40)

        # --- Test Suites Summary ---
        suite_pass, suite_fail, suite_mixed, suite_skip = self._get_suite_summary_counts()
        total_suites = len(self.results)
        suite_pass_percent = (suite_pass / total_suites * 100) if total_suites > 0 else 0
        lines.append("\nSUMMARY (Test Suites)")
        lines.append(f"Total Test Suites: {total_suites}")
        lines.append(f"PASS: {suite_pass} ({suite_pass_percent:.2f}%), FAIL: {suite_fail}, MIXED: {suite_mixed}, SKIP: {suite_skip}")

        # --- Individual Tests Summary ---
        metric_pass, metric_fail, metric_skip = self._get_metric_summary_counts()
        total_metrics = metric_pass + metric_fail + metric_skip
        metric_pass_percent = (metric_pass / total_metrics * 100) if total_metrics > 0 else 0
        lines.append("\nSUMMARY (Individual Tests)")
        lines.append(f"Total Individual Tests: {total_metrics}")
        lines.append(f"PASS: {metric_pass} ({metric_pass_percent:.2f}%), FAIL: {metric_fail}, SKIP: {metric_skip}")

        return "\n".join(lines)

    def generate_html_report(self, timestamp):
        author_line = f"<div class='author-info'>Author: Bang Thien Nguyen <ontario1998@gmail.com></div>"
        build_line = f"<div class='author-info'>Build Number: {self.build_number} &nbsp;|&nbsp; Test Run Timestamp: {timestamp}</div>"

        # Navigation bar with absolute URLs (robust under GitHub Pages project path)
        nav_bar = f"""
        <div class="nav-bar">
          {LATEST_URL}Latest Report</a>
          {HISTORY_URL}Report History</a>
        </div>
        """

        scenario_html = ""
        for result in self.results:
            metric_html = ""
            # Iterate over all possible metrics from the status report
            for metric, status in sorted(result["metric_status"].items()):
                values = result["metrics"].get(metric)
                status_label = render_status_label(status)
                if values:
                    metric_html += f"""
                    <div class="metric-item">
                      <span class="metric-key">{metric}</span>
                      <span class="metric-value">Min: {values['min']} &nbsp; Max: {values['max']} &nbsp; Avg: {values['avg']} → {status_label}</span>
                    </div>
                    """
                else:
                    metric_html += f"""
                    <div class="metric-item">
                      <span class="metric-key">{metric}</span>
                      <span class="metric-value">Not available → {status_label}</span>
                    </div>
                    """

            status_color = STATUS_COLORS.get(result['scenario_status'], '#000')
            scenario_status_label = render_status_label(result['scenario_status'])
            scenario_html += f"""
            <div class="scenario-card">
              <h3>{result['scenario']}</h3>
              <div class="metric-group">
                {metric_html}
              </div>
              <div class="test-result" style="border-left: 4px solid {status_color}; background:#f9fafb; padding:8px; margin-top:10px;">
                Scenario Status: {scenario_status_label}
              </div>
            </div>
            """

        # --- Test Suites Summary HTML ---
        suite_pass, suite_fail, suite_mixed, suite_skip = self._get_suite_summary_counts()
        total_suites = len(self.results)
        suite_pass_percent = (suite_pass / total_suites * 100) if total_suites > 0 else 0
        suite_summary_html = f"""
        <div class="summary-card">
          <h2>Overall Summary (Test Suites)</h2>
          <div class="summary-item"><span class="summary-key">Total Test Suites</span><span class="summary-value">{total_suites}</span></div>
          <div class="summary-item"><span class="summary-key">PASS</span><span class="summary-value" style="color:{STATUS_COLORS['PASS']};">{suite_pass} ({suite_pass_percent:.2f}%)</span></div>
          <div class="summary-item"><span class="summary-key">FAIL</span><span class="summary-value" style="color:{STATUS_COLORS['FAIL']};">{suite_fail}</span></div>
          <div class="summary-item"><span class="summary-key">MIXED</span><span class="summary-value" style="color:{STATUS_COLORS['MIXED']};">{suite_mixed}</span></div>
          <div class="summary-item"><span class="summary-key">SKIP</span><span class="summary-value" style="color:{STATUS_COLORS['SKIP']};">{suite_skip}</span></div>
        </div>
        """

        # --- Individual Tests Summary HTML ---
        metric_pass, metric_fail, metric_skip = self._get_metric_summary_counts()
        total_metrics = metric_pass + metric_fail + metric_skip
        metric_pass_percent = (metric_pass / total_metrics * 100) if total_metrics > 0 else 0
        metric_summary_html = f"""
        <div class="summary-card" style="background-color: #e0f2fe; border-color: #7dd3fc; margin-top: 20px;">
          <h2>Overall Summary (Individual Tests)</h2>
          <div class="summary-item"><span class="summary-key">Total Individual Tests</span><span class="summary-value">{total_metrics}</span></div>
          <div class="summary-item"><span class="summary-key">PASS</span><span class="summary-value" style="color:{STATUS_COLORS['PASS']};">{metric_pass} ({metric_pass_percent:.2f}%)</span></div>
          <div class="summary-item"><span class="summary-key">FAIL</span><span class="summary-value" style="color:{STATUS_COLORS['FAIL']};">{metric_fail}</span></div>
          <div class="summary-item"><span class="summary-key">SKIP</span><span class="summary-value" style="color:{STATUS_COLORS['SKIP']};">{metric_skip}</span></div>
        </div>
        """

        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Compact Firmware Analysis Report</title>
  <style>
  body {{
    font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background-color: #f0f4f8; color: #1a202c; padding: 20px; margin: 0; line-height: 1.5;
  }}
  .container {{
    max-width: 1200px; margin: 0 auto; background-color: #ffffff; padding: 20px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 12px;
  }}
  h1 {{
    color: #1d4ed8; border-bottom: 3px solid #bfdbfe; padding-bottom: 10px; margin-bottom: 20px; font-size: 2em;
  }}
  .author-info {{ color: #4b5563; font-size: 0.9em; margin-bottom: 5px; }}
  /* --- NAVIGATION STYLES --- */
  .nav-bar {{
    display: flex; justify-content: flex-start; margin-bottom: 20px; border-bottom: 1px solid #d1d5db; padding-bottom: 10px;
  }}
  .nav-link {{
    text-decoration: none; color: #1d4ed8; font-weight: 600; padding: 5px 15px; margin-right: 10px;
    border: 1px solid #bfdbfe; border-radius: 6px; transition: background-color 0.2s;
  }}
  .nav-link:hover {{ background-color: #eff6ff; }}
  .nav-link-history {{ background-color: #dbeafe; }}
  /* --- Layout --- */
  .report-grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-top: 15px; }}
  @media (min-width: 768px) {{ .report-grid {{ grid-template-columns: 1fr 1fr; }} }}
  .scenario-card {{ background-color: #f9fafb; border: 1px solid #e5e7eb; padding: 15px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  .scenario-card h3 {{ color: #059669; font-size: 1.4em; margin: 0 0 10px 0; border-bottom: 2px solid #a7f3d0; padding-bottom: 5px; }}
  .metric-group {{ display: grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 15px; }}
  @media (min-width: 640px) {{ .metric-group {{ grid-template-columns: 1fr 1fr; }} }}
  @media (min-width: 1024px) {{ .metric-group {{ grid-template-columns: 1fr 1fr 1fr; }} }}
  .metric-item {{
    display: flex; justify-content: space-between; align-items: center; background-color: #ffffff;
    padding: 8px 12px; border-radius: 6px; border-left: 4px solid #fcd34d; font-size: 0.9em; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
  }}
  .metric-key {{ color: #4b5563; font-weight: 500; }}
  .metric-value {{ color: #1f2937; font-weight: 700; text-align: right; }}
  .summary-card {{ background-color: #dbeafe; border: 2px solid #93c5fd; padding: 20px; margin-top: 30px; border-radius: 10px; }}
  .summary-card h2 {{ color: #1e3a8a; font-size: 1.8em; margin: 0 0 15px 0; text-align: center; }}
  .summary-item {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted #93c5fd; }}
  .summary-key {{ font-weight: 600; color: #1f2937; }}
  .summary-value {{ font-weight: 700; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Firmware Performance Analysis Comprehensive Report</h1>
    {nav_bar}
    {author_line}
    {build_line}
    <div class="report-grid">
      {scenario_html}
    </div>
    {suite_summary_html}
    {metric_summary_html}
  </div>
</body>
</html>"""
        return html_output

    def _get_suite_summary_counts(self):
        """Counts the final status for each test suite."""
        pass_count = fail_count = mixed_count = skip_count = 0
        for result in self.results:
            status = result["scenario_status"]
            if status == "PASS":
                pass_count += 1
            elif status == "FAIL":
                fail_count += 1
            elif status == "MIXED":
                mixed_count += 1
            elif status == "SKIP":
                skip_count += 1
        return pass_count, fail_count, mixed_count, skip_count

    def _get_metric_summary_counts(self):
        """Counts the status of all individual tests (metrics) across all suites."""
        pass_count = fail_count = skip_count = 0
        for result in self.results:
            for status in result["metric_status"].values():
                if status == "PASS":
                    pass_count += 1
                elif status == "FAIL":
                    fail_count += 1
                elif status == "SKIP":
                    skip_count += 1
        return pass_count, fail_count, skip_count


# -------------------- MAIN ENTRY --------------------
def main():
    build_number = None
    if len(sys.argv) > 1:
        build_number = sys.argv[1]
    analyzer = FirmwarePerformanceAnalyzer(build_number=build_number)
    analyzer.analyze()
    analyzer.generate_reports()


if __name__ == "__main__":
    main()