#!/usr/bin/env python3
"""
Firmware Performance Monitor & Report Generator
------------------------------------------------
Generates detailed firmware performance analysis reports
in both TXT and HTML formats with scenario-based metrics.

Features:
- 6 fixed scenarios with dummy data
- Metrics evaluation (PASS/FAIL/SKIP) with thresholds
- Scenario-level status (PASS/FAIL/MIXED/SKIP)
- Auto-SKIP if metric missing
- Summary table at bottom of HTML
- Optional build number (CLI input)
- Reports saved in ./reports/ with local timestamp
"""

import os
import sys
import datetime
import pytz
from statistics import mean


# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------

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
    "PASS": "#10b981",   # green
    "FAIL": "#ef4444",   # red
    "SKIP": "#6b7280",   # gray
    "MIXED": "#f59e0b"   # amber
}

# -------------------------------------------------------------------
# DATASET: FIXED DUMMY DATA
# -------------------------------------------------------------------

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
            # Memory missing → will auto SKIP
            "Power (mW)": {"min": 15, "max": 40, "avg": 20},
            "Temperature (°C)": {"min": 30, "max": 40, "avg": 35},
            "Latency (us)": {"min": 500, "max": 2000, "avg": 1200},
        }
    }
]


# -------------------------------------------------------------------
# EVALUATION FUNCTIONS
# -------------------------------------------------------------------

def evaluate_metric(metric_name, values, thresholds):
    """Evaluate PASS/FAIL/SKIP for a given metric based on thresholds."""
    if not values or "avg" not in values:
        return "SKIP"
    avg_val = values["avg"]
    if metric_name in thresholds:
        if avg_val <= thresholds[metric_name]:
            return "PASS"
        else:
            return "FAIL"
    return "SKIP"


def evaluate_scenario(scenario_data, thresholds):
    """Evaluate metrics for one scenario and determine overall scenario status."""
    results = {}
    scenario_status = "PASS"
    found_skip, found_fail = False, False

    for metric, values in scenario_data["metrics"].items():
        status = evaluate_metric(metric, values, thresholds)
        results[metric] = status
        if status == "FAIL":
            scenario_status = "FAIL"
            found_fail = True
        elif status == "SKIP":
            found_skip = True

    # Mixed if PASS + SKIP but no FAIL
    if not found_fail and found_skip and scenario_status == "PASS":
        scenario_status = "MIXED"

    # If all skipped
    if all(v == "SKIP" for v in results.values()):
        scenario_status = "SKIP"

    return results, scenario_status


def render_status_label(status):
    """Return styled HTML span for status."""
    color = STATUS_COLORS.get(status, "#000000")
    return f'<span style="color:{color}; font-weight:bold;">{status}</span>'


# -------------------------------------------------------------------
# REPORT GENERATION
# -------------------------------------------------------------------

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
        # Ensure reports folder exists
        report_dir = os.path.join(os.getcwd(), "reports")
        os.makedirs(report_dir, exist_ok=True)

        # Local timezone timestamp
        local_tz = datetime.datetime.now().astimezone().tzinfo
        timestamp = datetime.datetime.now(local_tz).strftime("%Y%m%d_%H%M%S")

        # Filenames
        base_filename = f"firmware_analysis_report_{timestamp}"
        if self.build_number != "NA":
            base_filename += f"_{self.build_number}"

        txt_path = os.path.join(report_dir, base_filename + ".txt")
        html_path = os.path.join(report_dir, base_filename + ".html")

        # Generate text report
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.generate_text_report(timestamp))

        # Generate HTML report
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(self.generate_html_report(timestamp))

        print(f"Reports generated:\n- {txt_path}\n- {html_path}")

    # ----------------------------------------------------------------
    # TEXT REPORT
    # ----------------------------------------------------------------
    def generate_text_report(self, timestamp):
        lines = []
        lines.append("Firmware Performance Analysis Report")
        lines.append(f"Build Number: {self.build_number}")
        lines.append(f"Test Run Timestamp: {timestamp}")
        lines.append("="*60)

        for result in self.results:
            lines.append(f"Scenario: {result['scenario']}")
            for metric, values in result["metrics"].items():
                status = result["metric_status"].get(metric, "SKIP")
                if values:
                    lines.append(f"  {metric}: Min={values['min']} | Max={values['max']} | Avg={values['avg']} -> {status}")
                else:
                    lines.append(f"  {metric}: SKIP")
            lines.append(f"Scenario Status: {result['scenario_status']}")
            lines.append("-"*40)

        # Summary
        pass_count, fail_count, skip_count = self._get_summary_counts()
        lines.append("SUMMARY")
        lines.append(f"Total Scenarios: {len(self.results)}")
        lines.append(f"PASS: {pass_count}, FAIL: {fail_count}, SKIP: {skip_count}")

        return "\n".join(lines)

    # ----------------------------------------------------------------
    # HTML REPORT
    # ----------------------------------------------------------------
    def generate_html_report(self, timestamp):
        author_line = f"<div class='author-info'>Build Number: {self.build_number} | Test Run Timestamp: {timestamp}</div>"

        scenario_html = ""
        for result in self.results:
            metric_html = ""
            for metric, values in result["metrics"].items():
                status = result["metric_status"].get(metric, "SKIP")
                if values:
                    metric_html += f"""
                        <div class="metric-item">
                            <span class="metric-key">{metric}</span>
                            <span class="metric-value">Min: {values['min']} | Max: {values['max']} | Avg: {values['avg']} → {render_status_label(status)}</span>
                        </div>
                    """
                else:
                    metric_html += f"""
                        <div class="metric-item">
                            <span class="metric-key">{metric}</span>
                            <span class="metric-value">SKIP</span>
                        </div>
                    """
            scenario_html += f"""
                <div class="scenario-card">
                    <h3>{result['scenario']}</h3>
                    <div class="metric-group">
                        {metric_html}
                    </div>
                    <div class="test-result" style="border-left: 4px solid {STATUS_COLORS[result['scenario_status']]}; background:#f9fafb; padding:8px; margin-top:10px;">
                        Scenario Status: {render_status_label(result['scenario_status'])}
                    </div>
                </div>
            """

        # Summary
        pass_count, fail_count, skip_count = self._get_summary_counts()
        summary_html = f"""
            <div class="summary-card">
                <h2>Overall Summary</h2>
                <div class="summary-item"><span class="summary-key">Total Scenarios</span><span class="summary-value">{len(self.results)}</span></div>
                <div class="summary-item"><span class="summary-key">PASS</span><span class="summary-value" style="color:{STATUS_COLORS['PASS']};">{pass_count}</span></div>
                <div class="summary-item"><span class="summary-key">FAIL</span><span class="summary-value" style="color:{STATUS_COLORS['FAIL']};">{fail_count}</span></div>
                <div class="summary-item"><span class="summary-key">SKIP</span><span class="summary-value" style="color:{STATUS_COLORS['SKIP']};">{skip_count}</span></div>
            </div>
        """

        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Compact Firmware Analysis Report</title>
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #f0f4f8; color: #1a202c; padding: 20px; margin: 0; line-height: 1.5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: #ffffff; padding: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-radius: 12px; }}
        h1 {{ color: #1d4ed8; border-bottom: 3px solid #bfdbfe; padding-bottom: 10px; margin-bottom: 20px; font-size: 2em; }}
        .author-info {{ color: #4b5563; font-size: 0.9em; margin-bottom: 25px; border-bottom: 1px dashed #e5e7eb; padding-bottom: 10px; }}
        .report-grid {{ display: grid; grid-template-columns: 1fr; gap: 20px; margin-top: 15px; }}
        @media (min-width: 768px) {{ .report-grid {{ grid-template-columns: 1fr 1fr; }} }}
        .scenario-card {{ background-color: #f9fafb; border: 1px solid #e5e7eb; padding: 15px; margin-bottom: 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .scenario-card h3 {{ color: #059669; font-size: 1.4em; margin-top: 0; margin-bottom: 10px; border-bottom: 2px solid #a7f3d0; padding-bottom: 5px; }}
        .metric-group {{ display: grid; grid-template-columns: 1fr; gap: 10px; margin-bottom: 15px; }}
        @media (min-width: 640px) {{ .metric-group {{ grid-template-columns: 1fr 1fr; }} }}
        @media (min-width: 1024px) {{ .metric-group {{ grid-template-columns: 1fr 1fr 1fr; }} }}
        .metric-item {{ display: flex; justify-content: space-between; background-color: #ffffff; padding: 8px 12px; border-radius: 6px; border-left: 4px solid #fcd34d; font-size: 0.9em; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }}
        .metric-key {{ color: #4b5563; font-weight: 500; }}
        .metric-value {{ color: #1f2937; font-weight: 700; }}
        .summary-card {{ background-color: #dbeafe; border: 2px solid #93c5fd; padding: 20px; margin-top: 30px; border-radius: 10px; }}
        .summary-card h2 {{ color: #1e3a8a; font-size: 1.8em; margin-top: 0; margin-bottom: 15px; text-align: center; }}
        .summary-item {{ display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px dotted #93c5fd; }}
        .summary-key {{ font-weight: 600; color: #1f2937; }}
        .summary-value {{ font-weight: 700; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Firmware Performance Analysis Comprehensive Report</h1>
        {author_line}
        <div class="report-grid">
            {scenario_html}
        </div>
        {summary_html}
    </div>
</body>
</html>"""
        return html_output

    # ----------------------------------------------------------------
    # Helper for summary counts
    # ----------------------------------------------------------------
    def _get_summary_counts(self):
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


# -------------------------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------------------------

def main():
    build_number = None
    if len(sys.argv) > 1:
        build_number = sys.argv[1]

    analyzer = FirmwarePerformanceAnalyzer(build_number=build_number)
    analyzer.analyze()
    analyzer.generate_reports()


if __name__ == "__main__":
    main()
