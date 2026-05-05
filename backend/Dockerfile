FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
EXPOSE 3001

# Create startup script (will be overridden by volume mount in dev, but needed for production)
RUN echo '#!/bin/sh\n\
set -e\n\
echo "Running database migrations..."\n\
alembic upgrade head || echo "Migration failed or already up to date"\n\
echo "Starting server..."\n\
if [ "$RELOAD" = "true" ]; then\n\
  exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-3001} --reload\n\
else\n\
  exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-3001}\n\
fi\n\
' > /app/start.sh && chmod +x /app/start.sh

# Default command (can be overridden in docker-compose)
# Railway will set PORT env var, fallback to 3001 for local dev
# Use shell form to support env var substitution
CMD ["/app/start.sh"]
