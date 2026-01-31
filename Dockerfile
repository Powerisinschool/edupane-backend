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

# Grant execution rights to the script
RUN chmod +x render_start.sh

# Run the custom script instead of just daphne
CMD ["./render_start.sh"]
