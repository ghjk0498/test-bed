# Makefile - PostgreSQL Local Environment

.PHONY: up down clean status test

up:
	docker-compose up -d
	@echo "Waiting for PostgreSQL to start..."
	@powershell -Command "Start-Sleep -s 3"
	@echo "PostgreSQL container started."

down:
	docker-compose down

clean:
	docker-compose down -v
	@powershell -Command "if (Test-Path ./data) { Remove-Item -Recurse -Force ./data }"

status:
	python manage_db.py status

test:
	pytest tests/
