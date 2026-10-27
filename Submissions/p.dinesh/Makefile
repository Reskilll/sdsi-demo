# dag-scheduler — project command aliases
# Run these from the project root.

.PHONY: install test coverage lint clean run

# Install in editable mode with dev deps
install:
	pip install -e ".[dev]"

# Run the full test suite
test:
	python -m pytest tests/ -v

# Run tests with coverage report
coverage:
	python -m pytest tests/ -v --cov=src --cov-report=term-missing

# Quick smoke-test on all sample inputs
run:
	dag-scheduler samples/basic.json
	@echo "---"
	dag-scheduler samples/complex.json --workers 3
	@echo "---"
	dag-scheduler samples/cycle.json || true
	@echo "---"
	dag-scheduler samples/missing_dep.json || true
	@echo "---"
	dag-scheduler samples/complex.json --fail train_a
	@echo "---"
	dag-scheduler samples/basic.json --json
	@echo "---"
	dag-scheduler samples/basic.json --dot

# Lint check (if ruff is installed)
lint:
	ruff check src/ tests/

clean:
	rm -rf __pycache__ src/__pycache__ src/*.egg-info tests/__pycache__ .pytest_cache dist build *.egg-info