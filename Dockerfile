# Use Ubuntu 24.04 as base image
FROM ubuntu:24.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Update system and install required packages
RUN apt update && apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    curl ffmpeg \
    vainfo intel-media-va-driver-non-free \
    && apt clean && rm -rf /var/lib/apt/lists/*

# Set Python3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# Create a working directory
WORKDIR /app

# Copy application files (excluding empty directories)
COPY . /app

# Ensure following directories exist (for volume mounting)
# RUN mkdir -p /app/recording && chmod -R 777 /app/recording
# VOLUME ["/app/recording"]
# RUN mkdir -p /app/snapshots && chmod -R 777 /app/snapshots
# VOLUME ["/app/snapshots"]

# Create a virtual environment
RUN python3 -m venv /app/venv

# Activate virtual environment
ENV PATH="/app/venv/bin:$PATH"

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Expose FastAPI port
EXPOSE 8002

# Create a base image label
LABEL description="Production image with Python 3.12, FastAPI, and FFmpeg"

# Command to run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]