# Use official Python base image (Python 3.9 slim version)
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Set environment variables to prevent Python from writing pyc files and to run in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies (if any needed - none needed for now)
# RUN apt-get update && apt-get install -y --no-install-recommends some-package && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container's working directory
COPY . .

# Expose the port the app runs on (standard port for Cloud Run is 8080)
EXPOSE 8080

# Command to run the application using uvicorn when the container starts
# Cloud Run injects the PORT environment variable, which uvicorn uses.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
