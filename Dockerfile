# Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y build-essential

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Run Daphne (not gunicorn)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "edupane_backend.asgi:application"]
