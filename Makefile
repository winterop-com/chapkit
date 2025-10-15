.PHONY: help install lint lint-servicekit lint-chapkit test test-servicekit test-chapkit coverage clean

# ==============================================================================
# Venv
# ==============================================================================

UV := $(shell command -v uv 2> /dev/null)
VENV_DIR?=.venv
PYTHON := $(VENV_DIR)/bin/python

# ==============================================================================
# Targets
# ==============================================================================

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Monorepo Targets:"
	@echo "  install           Install all dependencies"
	@echo "  lint              Run linter and type checker on all packages"
	@echo "  lint-servicekit   Lint servicekit only"
	@echo "  lint-chapkit      Lint chapkit only"
	@echo "  test              Run all tests"
	@echo "  test-servicekit   Test servicekit only"
	@echo "  test-chapkit      Test chapkit only"
	@echo "  coverage          Run tests with coverage reporting"
	@echo "  clean             Clean up temporary files"

install:
	@echo ">>> Installing workspace dependencies"
	@$(UV) sync --all-packages

lint:
	@echo ">>> Running linter on all packages"
	@$(UV) run ruff format .
	@$(UV) run ruff check . --fix
	@echo ">>> Running type checkers"
	@$(UV) run mypy packages/servicekit/src packages/chapkit/src
	@$(UV) run pyright

lint-servicekit:
	@echo ">>> Linting servicekit"
	@$(UV) run ruff format packages/servicekit
	@$(UV) run ruff check packages/servicekit --fix
	@$(UV) run mypy packages/servicekit/src

lint-chapkit:
	@echo ">>> Linting chapkit"
	@$(UV) run ruff format packages/chapkit
	@$(UV) run ruff check packages/chapkit --fix
	@$(UV) run mypy packages/chapkit/src

test:
	@echo ">>> Running all tests"
	@$(UV) run env PYTHONPATH="$${PWD}/packages/servicekit/src:$${PWD}/packages/chapkit/src:$${PWD}/examples" pytest packages/servicekit/tests packages/chapkit/tests -q

test-servicekit:
	@echo ">>> Testing servicekit"
	@$(UV) run env PYTHONPATH="$${PWD}/packages/servicekit/src:$${PWD}/packages/chapkit/src:$${PWD}/examples" pytest packages/servicekit/tests -q

test-chapkit:
	@echo ">>> Testing chapkit"
	@$(UV) run env PYTHONPATH="$${PWD}/packages/servicekit/src:$${PWD}/packages/chapkit/src:$${PWD}/examples" pytest packages/chapkit/tests -q

coverage:
	@echo ">>> Running tests with coverage"
	@$(UV) run coverage run -m pytest packages/servicekit/tests packages/chapkit/tests -q
	@$(UV) run coverage report
	@$(UV) run coverage xml

clean:
	@echo ">>> Cleaning up"
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -delete
	@find . -type d -name ".ruff_cache" -delete
	@find . -type d -name ".mypy_cache" -delete

# ==============================================================================
# Default
# ==============================================================================

.DEFAULT_GOAL := help
