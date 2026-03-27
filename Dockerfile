# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies for PyMuPDF and standard tools
RUN apt-get update && apt-get install -y \
    build-essential \
    libmupdf-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in pyproject.toml
RUN pip install --no-cache-dir .

# Expose the port the app runs on
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=.

# Run uvicorn when the container launches
CMD ["python", "-m", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
