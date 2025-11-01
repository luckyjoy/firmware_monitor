# 💻 Firmware Performance Monitor & Report Generator

**A Self-Contained Python Framework for Firmware Performance Analysis and Scenario-Based Reporting.**

This repository, **`firmware_monitor`**, provides a comprehensive, self-contained solution for monitoring, analyzing, and tracking performance changes within firmware images. It processes structured log data against defined thresholds and generates detailed, scenario-based analysis reports in both **TXT** and **HTML** formats.

-----

-----

## 🛠️ End-to-End CI/CD & Deployment Workflow

This project is designed for automation, using **GitHub Actions** and a **Jenkins Declarative Pipeline** to ensure consistent analysis and image publishing.

### 1\. Analysis & Report Generation

  * The pipeline is triggered on a `push` or `pull_request` to the `main` branch.
  * The core command, `python firmware_monitor.py`, executes the analysis, evaluates metrics against thresholds, and generates the `report.html` and `report_history.html` files in the `reports/` directory.

### 2\. Packaging & Publishing

  * The **`Dockerfile`** defines a consistent container environment.
  * The Jenkins pipeline builds the Docker image and, on the `main` branch, tags and pushes it to a private registry.
  * The GitHub Actions workflow similarly builds and pushes the image to **GitHub Container Registry (GHCR)**.

### 3\. Deployment (Example)

  * The Jenkins pipeline includes an optional `Deploy` stage where steps can be added to trigger a final deployment to a target environment (e.g., Kubernetes or an Ansible playbook).

-----

## 💡 Project Overview

This framework processes structured log data to analyze the performance and stability of firmware under various scenarios (e.g., "Low Load Boot," "Thermal Stress," "Power Dip").

| **Component** | **Technology** | **Role** |
|---------------|----------------|----------|
| Analysis Engine | **Python (firmware\_monitor.py)** | Evaluates metrics against pre-defined thresholds (e.g., 80% CPU, 5000μs Latency). |
| Input Data | **MOCK\_LOG\_DATA (JSON/Dict)** | Structured data for CPU, Memory, Latency, Power, Temperature, and Boot Timestamps. |
| Reporting | **HTML/TXT Generation** | Creates human-readable reports with scenario status labels (PASS, FAIL, MIXED, SKIP). |
| Automation | **Jenkins / GitHub Actions** | Automates the entire analysis and containerization process. |

### 📊 Monitored Metrics (Thresholds for Failure)

The analysis tool tracks key system domains to ensure the firmware remains within acceptable performance limits:

  * **CPU (%)**: Max **80.0%**.
  * **Memory (KB)**: Max **900.0 KB**.
  * **Latency (us)**: Max **5000.0 μs**.
  * **Boot Timestamps (ms)**: Max **5000.0 ms**.
  * **Power (mW)**: Max **100.0 mW**.
  * **Temperature (°C)**: Max **85.0 °C**.

-----

## 🚀 Getting Started

### 🔧 Prerequisites

  - 🐍 **Python 3.x**
  - 🐳 **Docker**
  - ⚙️ **Git**

### ⚙️ Installation

Clone the repository and run the setup command:

```bash
git clone https://github.com/luckyjoy/firmware_monitor.git
cd firmware_monitor
# Install any required dependencies (if requirements.txt were present)
# pip install -r requirements.txt 
```

### 🧪 Run the Analysis

Execute the main script directly. This will generate the analysis reports in the local `reports/` directory.

```bash
python firmware_monitor.py
```

-----

## 🐳 Dockerized Execution

Use Docker to ensure the monitoring environment is consistent and reproducible.

### 1\. Build the Docker Image

Replace `v1.0.0` with your desired tag:

```bash
docker build -t firmware-monitor:v1.0.0 .
```

### 2\. Run the Container and Map Output

Run the container, mapping the internal `/app/reports` output directory to a local directory (`local_reports`) to retrieve the generated HTML and TXT files.

```bash
docker run -d \
    --name fm_production \
    -v $(pwd)/local_reports:/app/reports \
    firmware-monitor:v1.0.0
```

-----

## 🌳 Framework Architecture

```
firmware_monitor/
├── .github/                            # GitHub Actions workflow definitions
│   └── workflows/
│       └── ci.yml
├── config/                             # Configuration files (Placeholder)
├── Dockerfile                          # Defines the container image
├── Jenkinsfile                         # Jenkins Declarative Pipeline
├── README.md
├── requirements.txt                    # (Inferred)
├── firmware_monitor.py                 # Main analysis script (self-contained)
└── reports/                            # Generated HTML and TXT reports
    ├── report.html                     # Latest report
    ├── report_history.html             # List of unique reports
    └── firmware_analysis_report_*.html # Uniquely named reports
```

-----

## 🤝 Contributing Guidelines

1.  Fork the repository
2.  Create a feature branch
3.  Implement new scenarios, metrics, or reporting features
4.  Run `python firmware_monitor.py` locally and verify results
5.  Submit a Pull Request with a clear description

**Code Style:**

  - Follow **PEP8** conventions
  - Ensure **HTML/TXT reports** generate without errors
  - Document new logic and metrics within the code

-----

## 🪪 License

Released under the **MIT License** — free to use, modify, and distribute.

-----

📬 *Contact:* Bang Thien Nguyen [ontario1998@gmail.com](mailto:ontario1998@gmail.com)

-----

> *“Measure performance before you optimize — know your hardware before you test your code.”*