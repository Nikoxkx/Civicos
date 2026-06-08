FROM python:3.12-slim

WORKDIR /app

# System dependencies for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Install Playwright browsers
RUN playwright install chromium && playwright install-deps chromium

# Copy application code
COPY packages/ ./packages/

# Expose API port
EXPOSE 8000

CMD ["uvicorn", "packages.api.main:app", "--host", "0.0.0.0", "--port", "8000"]