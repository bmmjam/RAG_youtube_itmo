.PHONY: help clean install install-dev pre-commit-install lint fmt ruff black isort mypy test run-bot run-demo run-eval

PYTHON ?= python3

PROJECT_DIRS = app demo evaluation data_pipelines

clean:
	find . -type d -name '.mypy_cache' -exec rm -rf {} +
	find . -type d -name '__pycache__' -exec rm -rf {} +
	find . -type d -name '*pytest_cache*' -exec rm -rf {} +
	find . -type f -name "*.py[co]" -exec rm -rf {} +

# ==============================================================================
#  D E P E N D E N C I E S
# ==============================================================================

requirements:
	pip install --upgrade pip
	poetry install --sync
	make install-pre-commit

# ==============================================================================
#  P R E - C O M M I T
# ==============================================================================
install-pre-commit:
	@git config --global --add safe.directory /tmp
	@pre-commit install && pre-commit install --hook-type commit-msg

# ==============================================================================
#  L I N T & F O R M A T
# ==============================================================================


format: install-pre-commit
	@git config --global --add safe.directory /tmp
	pre-commit run --all-files


test:
	@if [ -d tests ]; then \
		echo "Running pytest..."; \
		pytest -q; \
	else \
		echo "No tests/ directory found, skipping pytest."; \
	fi

# ==============================================================================
#  R U N   P R O J E C T
# ==============================================================================

run-bot:
	$(PYTHON) app/app.py

run-demo:
	$(PYTHON) demo/rag.py

run-eval:
	$(PYTHON) evaluation/evaluator.py
