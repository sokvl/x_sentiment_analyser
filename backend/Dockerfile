FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalacja zależności systemowych + bibliotek dla Chrome/Selenium
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    wget \
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

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]