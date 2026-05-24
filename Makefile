.PHONY: help setup venv sync install-dev compile test test-unit test-integration lint check check-all format typecheck changelog-check doctor init-db coderabbit-review graph-check test-graph test-graph-memory test-graph-leaks check-file-size check-slots

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

check: venv ## Run Ruff lint with auto-fix and format
	$(PYTHON) -m ruff check --fix src tests
	$(PYTHON) -m ruff format src tests

check-all: check typecheck changelog-check ## Run all checks: check + typecheck + changelog
	@echo "$(GREEN)All checks passed!$(RESET)"

format: venv ## Format Python code with Ruff
	$(PYTHON) -m ruff format src tests

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
		echo "$(YELLOW)Running CodeRabbit review...$(RESET)" && time coderabbit review > .coderabbit-docs.md 2>&1; \
	else \
		echo "$(YELLOW)Running CodeRabbit via uv...$(RESET)" && time $(PYTHON) -m coderabbit review > .coderabbit-docs.md 2>&1; \
	fi

# ── Graph module checks ─────────────────────────────────────────────────────
check-file-size: ## Файлы graph/ ≤ 300 строк
	@echo "Checking file sizes in src/imbalance/graph/..."
	@fail=0; \
	for f in src/imbalance/graph/*.py; do \
		lines=$$(wc -l < "$$f"); \
		if [ "$$lines" -gt 300 ]; then \
			echo "  FAIL: $$f — $$lines lines (max 300)"; fail=1; \
		else \
			echo "  OK:   $$f — $$lines lines"; \
		fi; \
	done; \
	exit $$fail

check-slots: ## Проверка что все dataclasses в graph/ имеют slots=True
	@$(UV) run python -c "import ast, sys; from pathlib import Path; found = []; \
for f in Path('src/imbalance/graph').glob('*.py'): \
	t = ast.parse(f.read_text()); \
	for n in ast.walk(t): \
		if not isinstance(n, ast.ClassDef): continue; \
		for d in n.decorator_list: \
			if isinstance(d, ast.Call) and hasattr(d.func, 'id') and d.func.id == 'dataclass': \
				k = {x.arg: x.value for x in d.keywords}; \
				s = k.get('slots'); \
				if not (s and isinstance(s, ast.Constant) and s.value): found.append(f'{f}:{n.lineno} class {n.name}'); \
if found: [print(x) for x in found]; sys.exit(1 if found else 0); \
print('All graph dataclasses have slots=True ✓')"

test-graph: venv ## Unit + integration тесты graph-модуля
	$(PYTHON) -m pytest tests/graph/unit tests/graph/integration -v --tb=short -x

test-graph-memory: venv ## Memory тесты (медленные)
	$(PYTHON) -m pytest tests/graph/memory -v --tb=long -s

test-graph-leaks: venv ## Только leak-тесты с tracemalloc
	CHECK_LEAKS=1 $(PYTHON) -m pytest tests/graph/memory/test_no_leaks.py -v -s

graph-check: check-slots check-file-size lint test-graph ## Полная проверка graph