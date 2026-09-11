# Cleared2Bet — build offline-friendly (wheels/ préchargés sur l’hôte)
# make wheels  →  make dev-build

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
COPY wheels /wheels

# Préfère les wheels locales (make wheels) ; bascule PyPI si un paquet manque
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    || pip install --find-links=/wheels --retries 15 --timeout 120 -r requirements.txt

FROM python:3.11-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings \
    DJANGO_DEBUG=0 \
    GUNICORN_BIND=0.0.0.0:8000

WORKDIR /app

RUN groupadd --system django \
    && useradd --system --gid django --home /app --shell /usr/sbin/nologin django

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --chown=django:django . /app/

RUN mkdir -p /app/staticfiles /app/data /app/media /app/logs \
    && chown -R django:django /app/staticfiles /app/data /app/media /app/logs \
    && rm -rf /app/wheels

USER django
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/')"

ENTRYPOINT ["sh", "/app/deploy/docker-entrypoint.sh"]
CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "config.wsgi:application"]
