# Use ARG for Python version, default to 3.9
ARG PYTHON_VERSION=3.9
FROM python:${PYTHON_VERSION}-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY data/ ./data/

# Copy Alembic configuration and migrations
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy and set up migration script
COPY scripts/run_migrations.sh /run_migrations.sh
RUN chmod +x /run_migrations.sh

# Change ownership to non-root user
RUN chown -R appuser:appuser /app /run_migrations.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Set entrypoint to run migrations before starting the app
ENTRYPOINT ["/run_migrations.sh"]

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

