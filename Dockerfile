FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entrypoint script first and set permissions
COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh && \
    # Ensure script has Unix line endings
    sed -i 's/\r$//' /app/entrypoint.sh

# Copy the rest of the application
COPY . /app

# Create media directory
RUN mkdir -p /app/media/profile_pictures

# Use shell form for entrypoint to ensure proper execution
CMD ["/bin/bash", "/app/entrypoint.sh"]