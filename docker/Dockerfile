FROM python:3.11-slim

# 1.13: Install Foundry without curl|bash – download pinned binary directly
ARG FOUNDRY_TAG=nightly-2024-02-01

RUN apt-get update && \
    apt-get install -y --no-install-recommends git build-essential libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info curl && \
    rm -rf /var/lib/apt/lists/*

# 1.12: Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install slither-analyzer
RUN pip install --no-cache-dir slither-analyzer

# 1.13: Install Foundry by downloading release tarball (not curl|bash)
RUN curl -L -o /tmp/foundry.tar.gz \
      "https://github.com/foundry-rs/foundry/releases/download/${FOUNDRY_TAG}/foundry_${FOUNDRY_TAG}_linux_amd64.tar.gz" && \
    tar -xzf /tmp/foundry.tar.gz -C /usr/local/bin/ && \
    rm /tmp/foundry.tar.gz && \
    chmod +x /usr/local/bin/forge /usr/local/bin/cast /usr/local/bin/anvil /usr/local/bin/chisel 2>/dev/null || true

# Create directories that the app needs
RUN mkdir -p /app/uploads /app/chroma_data /app/reports && \
    chown -R appuser:appuser /app

COPY backend/ .

# 1.12: Ensure all files are accessible by appuser
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

VOLUME ["/app/chroma_data", "/app/uploads", "/app/reports"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
