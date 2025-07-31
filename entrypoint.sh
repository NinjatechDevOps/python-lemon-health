#!/bin/bash

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h db -p 5432 -U postgres; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Seed initial prompts
echo "Seeding initial prompts..."
python -m scripts.seed_prompts

# Start the application
echo "Starting the application..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload 