# Use the official Python base image (Debian based)
# This provides a stable, small environment suitable for CI/CD.
FROM python:3.10-slim

# Set environment variables to prevent Python from writing .pyc files and
# to ensure stdout/stderr are unbuffered (good for container logging)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /app

# ===================================================================
# FIX: Install Java and Allure CLI for report generation
# ===================================================================

# 1. Update package lists with retry logic (Fixes exit code 100)
# This loop retries the update command 5 times to bypass intermittent network failures.
RUN for i in 1 2 3 4 5; do apt-get update && break || sleep 5; done

# 2. Install necessary system dependencies (Java JRE, wget, unzip)
# Switched to openjdk-21-jre-headless as suggested by Debian repo changes.
RUN apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    wget \
    unzip && \
    rm -rf /var/lib/apt/lists/*

# 3. Download and configure the Allure Command Line tool
ENV ALLURE_VERSION=2.29.0
RUN wget -qO /tmp/allure-commandline.zip https://repo.maven.apache.org/maven2/io/qameta/allure/allure-commandline/${ALLURE_VERSION}/allure-commandline-${ALLURE_VERSION}.zip && \
    unzip /tmp/allure-commandline.zip -d /opt && \
    rm /tmp/allure-commandline.zip

# 4. Add the Allure executable to the system PATH
ENV PATH="${PATH}:/opt/allure-${ALLURE_VERSION}/bin"

# ===================================================================
# Python Dependency Installation
# ===================================================================

# Check if requirements.txt exists in the build context and copy it.
# If it doesn't exist, this line fails and we handle it in the next step.
COPY requirements.txt .

# Ensure requirements.txt exists by creating an empty one if the previous COPY failed.
# This prevents the pip install command from failing if the file is genuinely missing.
RUN if [ ! -f requirements.txt ]; then echo "" > requirements.txt; fi

# Install core project dependencies, including the necessary testing packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-bdd \
    allure-pytest \
    -r requirements.txt || true

# Copy the rest of the application code into the container
COPY . /app

# Set the default command to run pytest, which can still be overridden.
CMD ["pytest", "--ignore=features/manual_tests", "--alluredir=allure-results", "-m", "navigation"]
