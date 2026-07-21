FROM python:3.11-slim

# 1.13: Install Foundry without curl|bash – download pinned binary directly
ARG FOUNDRY_TAG=nightly-2024-02-01

RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && \
    apt-get install -y --no-install-recommends git build-essential libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info curl && \
    rm -rf /var/lib/apt/lists/*

# 1.12: Create non-root user
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser

WORKDIR /app

COPY --chown=appuser:appuser backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# Install sentence-transformers for local embedding
RUN pip install --no-cache-dir sentence-transformers -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# Install slither-analyzer
RUN pip install --no-cache-dir slither-analyzer -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com

# 1.13: Install Foundry v1.7.1 from GitHub release (static binary, works on any Linux)
RUN curl -L -o /tmp/foundry.tar.gz \
      "https://github.com/foundry-rs/foundry/releases/download/v1.7.1/foundry_v1.7.1_alpine_amd64.tar.gz" && \
    tar -xzf /tmp/foundry.tar.gz -C /usr/local/bin/ && \
    rm /tmp/foundry.tar.gz && \
    chmod +x /usr/local/bin/forge /usr/local/bin/cast /usr/local/bin/anvil /usr/local/bin/chisel

# Create directories that the app needs
RUN mkdir -p /app/uploads /app/chroma_data /app/reports

COPY --chown=appuser:appuser backend/ .

# Ensure all files are accessible by appuser
RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

VOLUME ["/app/chroma_data", "/app/uploads", "/app/reports"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
