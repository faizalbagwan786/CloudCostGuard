# Multi-stage Dockerfile for CloudCostGuard
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final Runtime Image
FROM python:3.12-slim

# Create non-root system user for security
RUN groupadd -r finops && useradd -r -g finops -d /home/finops -m finops

WORKDIR /app

# Copy installed wheels from builder stage
COPY --from=builder /root/.local /home/finops/.local
ENV PATH=/home/finops/.local/bin:$PATH
ENV PYTHONPATH=/app/src

COPY src /app/src
COPY pyproject.toml /app/

RUN chown -R finops:finops /app
USER finops

ENTRYPOINT ["python", "-m", "cloudcostguard.cli"]
CMD ["scan", "--demo"]
