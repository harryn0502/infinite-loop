# Use an official Python runtime as a parent image
FROM python:3.11-slim

# --- ADD THIS SECTION ---
# Install curl so the healthcheck can run
RUN apt-get update && apt-get install -y curl && \
    # Clean up the cache to keep the image slim
    rm -rf /var/lib/apt/lists/*
# ------------------------

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app /app/app

# The port your app will run on
EXPOSE 8000