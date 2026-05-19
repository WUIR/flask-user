.PHONY: install run migrate upgrade test lint docker-build docker-up deploy

install:
	pip install -r requirements.txt

run:
	flask run --host=0.0.0.0 --port=5000

migrate:
	flask db migrate -m "auto"

upgrade:
	flask db upgrade

test:
	pytest

lint:
	ruff check app/ tests/

docker-build:
	docker build -f docker/Dockerfile -t flask-user .

docker-up:
	docker compose -f docker/docker-compose.yml up -d

deploy:
	bash scripts/deploy.sh
