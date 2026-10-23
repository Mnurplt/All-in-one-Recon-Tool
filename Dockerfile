# Multi-platform Python base image (Linux, macOS/ARM, Windows)
FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=UTF-8

# Set working directory inside container
WORKDIR /app

# Install dependencies first to leverage Docker layer caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . /app/

# Security best practice: Run as non-root user
RUN useradd -m -u 1000 reconuser && \
    chown -R reconuser:reconuser /app
USER reconuser

# Set the entrypoint to the CLI tool
ENTRYPOINT ["python", "recon.py"]

# Default argument displays help if no target is provided
CMD ["--help"]
