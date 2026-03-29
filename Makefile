# Zmienna dla powtarzającej się ścieżki (opcjonalnie, dla czystości kodu)
COMPOSE = docker compose --env-file ./backend/.env

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

logs:
	$(COMPOSE) logs -f

seed:
	$(COMPOSE) exec api python manage.py loaddata default_tickers default_config

start: rebuild migrate seed