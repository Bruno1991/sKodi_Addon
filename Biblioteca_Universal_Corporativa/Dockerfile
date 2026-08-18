# syntax=docker/dockerfile:1.7
FROM python:3.12.8-slim-bookworm AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY web-scripting/python ./security
COPY services/reference-api ./service
RUN python -m venv /venv \
 && /venv/bin/pip install --upgrade "pip==24.3.1" "build==1.2.2.post1" \
 && /venv/bin/pip wheel --wheel-dir /wheels ./security \
 && /venv/bin/pip wheel --wheel-dir /wheels --find-links /wheels ./service

FROM python:3.12.8-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/venv/bin:$PATH
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /nonexistent --shell /usr/sbin/nologin app \
 && python -m venv /opt/venv
COPY --from=builder /wheels /wheels
RUN /opt/venv/bin/pip install --no-cache-dir --no-index --find-links /wheels mbuc-reference-api \
 && rm -rf /wheels \
 && find /opt/venv -type d -name __pycache__ -prune -exec rm -rf '{}' '+'
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).read()"]
ENTRYPOINT ["uvicorn", "reference_api.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--proxy-headers"]
