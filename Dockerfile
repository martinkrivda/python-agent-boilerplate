FROM python:3.14-slim AS builder

WORKDIR /app

RUN pip install uv --quiet

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app/ ./app/

FROM python:3.14-slim

WORKDIR /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

COPY --from=builder /app /app
COPY --from=builder /root/.local /root/.local

ENV PATH="/root/.local/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Build provenance — pass via `docker build --build-arg BUILD_COMMIT=... --build-arg BUILD_TIMESTAMP=...`
# (the Makefile `make docker-build` target does this automatically from git + date).
ARG BUILD_COMMIT=""
ARG BUILD_TIMESTAMP=""
ENV BUILD_COMMIT=${BUILD_COMMIT}
ENV BUILD_TIMESTAMP=${BUILD_TIMESTAMP}

# OCI image labels — standard metadata visible via `docker inspect`.
LABEL org.opencontainers.image.title="python-agent-boilerplate" \
      org.opencontainers.image.revision="${BUILD_COMMIT}" \
      org.opencontainers.image.created="${BUILD_TIMESTAMP}"

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
