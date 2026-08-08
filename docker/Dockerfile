# ===== Stage 1: Build dependencies =====
FROM python:3.11-slim AS builder

WORKDIR /build

COPY backend/requirements.txt .

RUN pip install --no-cache-dir --prefix=/install \
    -r requirements.txt \
    sentence-transformers \
    slither-analyzer

# ===== Stage 2: Runtime =====
FROM python:3.11-slim AS runtime

ARG FOUNDRY_TAG=v1.7.1

# 安装运行时系统依赖（不含编译工具）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libffi8 \
        shared-mime-info \
        curl \
        git && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 Python 包
COPY --from=builder /install /usr/local

# 安装 Foundry（静态二进制）
RUN curl -L -o /tmp/foundry.tar.gz \
      "https://github.com/foundry-rs/foundry/releases/download/${FOUNDRY_TAG}/foundry_${FOUNDRY_TAG}_linux_amd64.tar.gz" && \
    tar -xzf /tmp/foundry.tar.gz -C /usr/local/bin/ && \
    rm /tmp/foundry.tar.gz && \
    chmod +x /usr/local/bin/forge /usr/local/bin/cast /usr/local/bin/anvil /usr/local/bin/chisel

# 创建非 root 用户
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser

WORKDIR /app

# 创建应用目录
RUN mkdir -p /app/uploads /app/chroma_data /app/reports

# 复制应用代码
COPY --chown=appuser:appuser backend/ .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

VOLUME ["/app/chroma_data", "/app/uploads", "/app/reports"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
