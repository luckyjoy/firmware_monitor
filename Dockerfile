# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# This ensures the 'pytz' library is included in the image
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script into the container
COPY firmware_monitor.py .

# Define the command to run your script
CMD ["python", "firmware_monitor.py"]