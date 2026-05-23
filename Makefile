.PHONY: help setup venv sync install-dev compile test test-unit test-integration lint format typecheck changelog-check doctor init-db coderabbit-review

UV ?= uv
UV_PYTHON ?= 3.14
UV_CACHE_DIR ?= .uv-cache
UV_PYTHON_INSTALL_DIR ?= .uv-python
DEV_DATA_DIR ?= .data/imbalance

# Colors for help output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
BLUE := \033[0;34m
CYAN := \033[0;36m
RESET := \033[0m

# Python from .venv if exists, otherwise use uv run
ifneq ($(wildcard .venv/bin/python),)
  PYTHON := .venv/bin/python
else
  PYTHON := $(UV) run
endif

help: ## Show this help message
	@printf "$(CYAN)Usage:$(RESET)\n"
	@printf "  $(GREEN)make$(RESET) [target]\n\n"
	@printf "$(CYAN)Targets:$(RESET)\n"
	@awk 'BEGIN {FS = ":.*## "; max=0} \
		/^[a-zA-Z0-9_-]+:.*## / { \
			if (length($$1) > max) max = length($$1) \
		} \
		END { \
			max = max + 2; \
		} \
		/^[a-zA-Z0-9_-]+:.*## / { \
			printf "  $(YELLOW)%-$(max)s$(RESET) %s\n", $$1, $$2 \
		}' $(MAKEFILE_LIST)

venv: ## Create .venv virtual environment
	@test -d .venv || $(UV) venv --python $(UV_PYTHON) .venv
	@printf "$(GREEN).venv created$(RESET)\n"

setup: venv sync ## Setup complete development environment

sync: venv ## Create/update local .venv with uv
	$(UV) sync --extra dev

install-dev: sync ## Alias for sync

compile: venv ## Compile source and tests without importing external dependencies
	$(PYTHON) -m compileall src tests

test: test-unit test-integration ## Run unit and integration tests

test-unit: venv ## Run unit tests
	$(PYTHON) -m pytest tests/unit

test-integration: venv ## Run SQLite integration tests
	$(PYTHON) -m pytest tests/integration

lint: venv ## Run Ruff lint
	$(PYTHON) -m ruff check src tests

format: venv ## Format Python code with Ruff
	$(PYTHON) -m ruff format src tests
	$(PYTHON) -m ruff check --fix src tests

typecheck: venv ## Run mypy
	$(PYTHON) -m mypy src

changelog-check: ## Validate git-cliff changelog generation
	git-cliff --unreleased --tag unreleased --config cliff.toml

doctor: venv ## Run imbalance doctor for current project
	IMBALANCE_DATA_DIR=$(DEV_DATA_DIR) $(PYTHON) -m imbalance.cli.app doctor

init-db: venv ## Initialize the current project's SQLite database
	IMBALANCE_DATA_DIR=$(DEV_DATA_DIR) $(PYTHON) -m imbalance.cli.app init-db

coderabbit-review: venv ## Run CodeRabbit review and save report to .coderabbit-docs.md
	@if command -v coderabbit >/dev/null 2>&1; then \
		echo "$(YELLOW)Running CodeRabbit review...$(RESET)" && time coderabbit review > .coderabbit-docs.md 2>&1 || echo "$(RED)coderabbit failed$(RESET)"; \
	else \
		echo "$(YELLOW)Running CodeRabbit via uv...$(RESET)" && time $(PYTHON) -m coderabbit review > .coderabbit-docs.md 2>&1 || echo "$(RED)coderabbit not installed or failed$(RESET)"; \
	fi