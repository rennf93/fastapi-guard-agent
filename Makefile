# Supported Python versions
PYTHON_VERSIONS = 3.10 3.11 3.12 3.13 3.14
DEFAULT_PYTHON = 3.10

# Install dependencies
.PHONY: install
install:
	@uv sync
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Install dev dependencies
.PHONY: install-dev
install-dev:
	@uv sync --extra dev
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Update dependencies
.PHONY: lock
lock:
	@uv lock
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Upgrade dependencies
.PHONY: upgrade
upgrade:
	@uv lock --upgrade
	@uv sync --all-extras
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Stop
.PHONY: stop
stop:
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Lint code
.PHONY: lint
lint:
	@COMPOSE_BAKE=true docker compose run --rm --no-deps fastapi-guard-agent sh -c "echo 'Formatting w/ Ruff...' ; echo '' ; ruff format . ; echo '' ; echo '' ; echo 'Linting w/ Ruff...' ; echo '' ; ruff check . ; echo '' ; echo '' ; echo 'Type checking w/ Mypy...' ; echo '' ; mypy ."
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Fix code
.PHONY: fix
fix:
	@echo "Fixing formatting w/ Ruff..."
	@echo ''
	@uv run ruff check --fix .
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Run tests (default Python version)
.PHONY: test
test:
	@COMPOSE_BAKE=true PYTHON_VERSION=$(DEFAULT_PYTHON) docker compose run --rm --build fastapi-guard-agent pytest -v --cov=.
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Run All Python versions
.PHONY: test-all
test-all: test-3.10 test-3.11 test-3.12 test-3.13 test-3.14

# Python 3.10
.PHONY: test-3.10
test-3.10:
	@docker compose down -v fastapi-guard-agent
	@COMPOSE_BAKE=true PYTHON_VERSION=3.10 docker compose build fastapi-guard-agent
	@PYTHON_VERSION=3.10 docker compose run --rm fastapi-guard-agent pytest -v --cov=.
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Python 3.11
.PHONY: test-3.11
test-3.11:
	@docker compose down -v fastapi-guard-agent
	@COMPOSE_BAKE=true PYTHON_VERSION=3.11 docker compose build fastapi-guard-agent
	@PYTHON_VERSION=3.11 docker compose run --rm fastapi-guard-agent pytest -v --cov=.
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Python 3.12
.PHONY: test-3.12
test-3.12:
	@docker compose down -v fastapi-guard-agent
	@COMPOSE_BAKE=true PYTHON_VERSION=3.12 docker compose build fastapi-guard-agent
	@PYTHON_VERSION=3.12 docker compose run --rm fastapi-guard-agent pytest -v --cov=.
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Python 3.13
.PHONY: test-3.13
test-3.13:
	@docker compose down -v fastapi-guard-agent
	@COMPOSE_BAKE=true PYTHON_VERSION=3.13 docker compose build fastapi-guard-agent
	@PYTHON_VERSION=3.13 docker compose run --rm fastapi-guard-agent pytest -v --cov=.
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Python 3.14
.PHONY: test-3.14
test-3.14:
	@docker compose down -v fastapi-guard-agent
	@COMPOSE_BAKE=true PYTHON_VERSION=3.14 docker compose build fastapi-guard-agent
	@PYTHON_VERSION=3.14 docker compose run --rm fastapi-guard-agent pytest -v --cov=.
	@docker compose down --rmi all --remove-orphans -v
	@docker system prune -f

# Local testing
.PHONY: local-test
local-test:
	@uv run pytest -v --cov=.
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Serve docs
.PHONY: serve-docs
serve-docs:
	@uv run mkdocs serve
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Lint documentation
.PHONY: lint-docs
lint-docs:
	@uv run pymarkdownlnt scan -r -e ./.venv -e ./.git -e ./.github -e ./data -e ./guard -e ./tests .
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Fix documentation
.PHONY: fix-docs
fix-docs:
	@uv run pymarkdownlnt fix -r -e ./.venv -e ./data -e ./guard -e ./tests .
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Prune
.PHONY: prune
prune:
	@docker system prune -f

# Clean Cache Files
.PHONY: clean
clean:
	@find . | grep -E "(__pycache__|\\.pyc|\\.pyo|\\.pytest_cache|\\.ruff_cache|\\.mypy_cache)" | xargs rm -rf

# Version Management
.PHONY: bump-version
bump-version:
	@if [ -z "$(VERSION)" ]; then echo "Usage: make bump-version VERSION=x.y.z"; exit 1; fi
	@uv run python .github/scripts/bump_version.py $(VERSION)

# Help
.PHONY: help
help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

# Python versions list
.PHONY: show-python-versions
show-python-versions:
	@echo "Supported Python versions: $(PYTHON_VERSIONS)"
	@echo "Default Python version: $(DEFAULT_PYTHON)"
