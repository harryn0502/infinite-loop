# Use an official Python runtime as a parent image [cite: 1]
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first
COPY requirements.txt .

# Install any needed packages specified in requirements.txt [cite: 2]
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
# This is now *optional* for dev, but good practice
# in case the volume mount fails.
COPY ./app /app/app

# The port your app will run on
EXPOSE 8000

# We no longer need a CMD here,
# because the docker-compose.yml 'command' overrides it.