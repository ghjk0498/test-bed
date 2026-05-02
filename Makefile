# Makefile - Multi-Service Infrastructure Management

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================
.PHONY: lint test

lint:
	ruff check . --fix
	mypy .
	black .

test:
	pytest

