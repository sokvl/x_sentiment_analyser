COMPOSE = docker compose --env-file ./backend/.env
COMPOSE_PROD = docker compose -f docker-compose.prod.yaml --env-file ./backend/.env

up:
	$(COMPOSE) up

rebuild:
	$(COMPOSE) up --build

test:
	$(COMPOSE) exec api python manage.py test

down:
	$(COMPOSE) down

migrate:
	$(COMPOSE) exec api python manage.py migrate

migrations:
	$(COMPOSE) exec api python manage.py makemigrations


logs:
	$(COMPOSE) logs -f

seed:
	$(COMPOSE) exec api python manage.py loaddata default_tickers default_config

start: rebuild migrate seed

up-prod:
	$(COMPOSE_PROD) up -d --build

down-prod:
	$(COMPOSE_PROD) down