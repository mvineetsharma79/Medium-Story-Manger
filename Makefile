# Makefile for easy Docker management

.PHONY: help build up down logs shell clean dev prod

help:
	@echo "Available commands:"
	@echo "  make dev      - Start development mode with hot reload"
	@echo "  make prod     - Start production mode"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start containers (uses dev by default)"
	@echo "  make down     - Stop containers"
	@echo "  make logs     - View container logs"
	@echo "  make shell    - Open shell in development container"
	@echo "  make clean    - Remove containers, volumes, and images"

build:
	docker-compose build

dev:
	docker-compose up story-manager-dev

prod:
	docker-compose up story-manager-prod

up:
	docker-compose up -d

down:
	docker-compose down

logs:
	docker-compose logs -f

shell:
	docker-compose exec story-manager-dev /bin/bash

clean:
	docker-compose down -v
	docker system prune -f