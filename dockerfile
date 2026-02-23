# ---- Base image ----
FROM python:3.11-slim

# Prevent Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

# ---- System deps (optional but useful) ----
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ---- App directory ----
WORKDIR /app

# ---- Copy dependency files first (better caching) ----
COPY requirements.txt .
RUN pip install -r requirements.txt

# If pyproject contains runtime deps, install package
COPY pyproject.toml .
COPY src ./src
RUN pip install .

# ---- Expose MCP port (change if different) ----
EXPOSE 3000

# ---- Default command ----
CMD ["python", "-m", "jenkins_mcp_server"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -m jenkins_mcp_server --help || exit 1