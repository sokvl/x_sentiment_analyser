FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalacja zależności systemowych + bibliotek dla Chrome/Selenium
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    wget \
    curl \
    gnupg \
    unzip \
    ca-certificates \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libasound2 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/req.txt

COPY . .

RUN chmod +x docker-entrypoint.sh \
    && groupadd --system app && useradd --system --gid app --home-dir /app app \
    && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health/ || exit 1
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD gunicorn stocknlp.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}"