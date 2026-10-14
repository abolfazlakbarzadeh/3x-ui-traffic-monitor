.PHONY: up down logs test install-backend install-frontend build

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app

install-backend:
	cd backend && pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

test:
	cd backend && pytest -v

build:
	docker compose build
