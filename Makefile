.PHONY: install lint test experiments receipts evidence diagram verify regen clean

PY ?= python3

install:
	$(PY) -m pip install -e ".[dev,viz]"

lint:
	ruff check src tests experiments tools

test:
	$(PY) -m pytest -q --cov=earned_value --cov-report=term-missing \
		--junitxml=reports/junit.xml --cov-report=json:reports/coverage.json

experiments:
	$(PY) experiments/decompose_the_gap.py
	$(PY) experiments/find_the_illusion.py
	$(PY) experiments/forecast_vs_final.py
	$(PY) experiments/spi_blindness.py

# receipts assumes `make test` has written reports/junit.xml and reports/coverage.json.
receipts:
	$(PY) tools/collect_metrics.py --skip-tests
	$(PY) tools/check_numbers.py

diagram:
	$(PY) tools/render_diagram.py

evidence: diagram
	$(PY) tools/make_evidence.py

# regen rebuilds the committed fixture. It is NOT part of verify, because the
# published figures are reproduced from the committed data/program.csv, not from a
# fresh random draw. See ADR-004: regen needs the pinned numpy to match the figures.
regen:
	$(PY) -m earned_value.cli generate

verify: lint test receipts

clean:
	rm -rf reports .pytest_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
