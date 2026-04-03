.PHONY: check test lint regen clean

SPEC := PALS_LAW-v1.5.4.md

# Run the full audit (no network verification) and regenerate output JSON
regen:
	python3 -m pals_check $(SPEC) --no-verify

# Run the full audit with network verification
regen-verify:
	python3 -m pals_check $(SPEC)

# Run tests with coverage
test:
	python3 -m pytest tests/ --cov=pals_check --cov-report=term-missing -v

# Run linter
lint:
	python3 -m ruff check pals_check/ tests/
	python3 -m ruff format --check pals_check/ tests/

# Full check: lint + test + regenerate and diff
check: lint test
	@echo "--- Regenerating outputs and checking for drift ---"
	@python3 -m pals_check $(SPEC) --no-verify > /dev/null
	@if git diff --quiet output/ 2>/dev/null; then \
		echo "OK: Output JSON files are up to date."; \
	else \
		echo "DRIFT: Output JSON files have changed. Review and commit."; \
		git diff --stat output/ 2>/dev/null || true; \
	fi

clean:
	rm -rf __pycache__ pals_check/__pycache__ tests/__pycache__ .pytest_cache
	rm -rf .coverage htmlcov
