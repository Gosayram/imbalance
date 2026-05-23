.PHONY: help sync install-dev compile test test-unit test-integration lint format typecheck changelog-check doctor init-db

UV ?= uv
UV_CACHE_DIR ?= .uv-cache
UV_RUN = UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV)
DEV_DATA_DIR ?= .data/imbalance

help:
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "%-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

sync: ## Create/update local .venv with uv
	$(UV_RUN) sync --extra dev

install-dev: sync ## Alias for sync

compile: ## Compile source and tests without importing external dependencies
	$(UV_RUN) run python -m compileall src tests

test: test-unit test-integration ## Run unit and integration tests

test-unit: ## Run unit tests
	$(UV_RUN) run pytest tests/unit

test-integration: ## Run SQLite integration tests
	$(UV_RUN) run pytest tests/integration

lint: ## Run Ruff lint
	$(UV_RUN) run ruff check src tests

format: ## Format Python code with Ruff
	$(UV_RUN) run ruff format src tests
	$(UV_RUN) run ruff check --fix src tests

typecheck: ## Run mypy
	$(UV_RUN) run mypy src

changelog-check: ## Validate git-cliff changelog generation
	git-cliff --unreleased --tag unreleased --config cliff.toml

doctor: ## Run imbalance doctor for current project
	IMBALANCE_DATA_DIR=$(DEV_DATA_DIR) $(UV_RUN) run python -m imbalance.cli.app doctor

init-db: ## Initialize the current project's SQLite database
	IMBALANCE_DATA_DIR=$(DEV_DATA_DIR) $(UV_RUN) run python -m imbalance.cli.app init-db
