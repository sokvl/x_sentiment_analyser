FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    build-essential libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/req.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]