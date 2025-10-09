# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the script into the container
COPY firmware_monitor.py .

# Define the command to run your script
# The arguments for the build number will be passed when running the container
CMD ["python", "firmware_monitor.py"]