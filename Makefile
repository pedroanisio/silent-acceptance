.PHONY: check test lint regen regen-verify pdf lint-code clean

SPEC := SILENT_ACCEPTANCE-v2.0.0.md
PDF_OUT := output/SILENT_ACCEPTANCE-v2.0.0.pdf

# Run the full audit (no network verification) and regenerate output JSON
regen:
	python3 -m pals_check $(SPEC) --no-verify

# Run the full audit with network verification
regen-verify:
	python3 -m pals_check $(SPEC)

# Run tests with coverage
test:
	python3 -m pytest tests/ --cov=pals_check --cov-report=term-missing -v

# Render the specification to PDF (pandoc + lualatex)
pdf:
	python3 -m tools.build_pdf $(SPEC) $(PDF_OUT)

# Run linter
lint:
	python3 -m ruff check pals_check/ tests/ tools/
	python3 -m ruff format --check pals_check/ tests/ tools/

# Lint the code-side verification-boundary check (silent-acceptance-lint)
lint-code:
	cd silent-acceptance-lint && node --test 'tests/*.test.ts'

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
