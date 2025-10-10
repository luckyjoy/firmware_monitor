# Dockerfile
# Use a Python base image that matches the environment used previously
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the Python script into the container
COPY firmware_monitor.py .

# Install necessary packages if there were any (currently none, but good practice)
# RUN pip install <package_name>

# Set the entry point to python, allowing arguments to be passed easily
ENTRYPOINT ["python"]