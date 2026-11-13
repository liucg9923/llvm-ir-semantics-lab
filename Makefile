.PHONY: setup unit check freeze accept baseline fixtures report
PYTHON ?= python3
setup:
	IRSEM_PYTHON=$(PYTHON) bash scripts/setup_python.sh
unit:
	PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
check:
	bash scripts/run_cpu.sh check-dataset
freeze:
	bash scripts/run_cpu.sh freeze
accept:
	bash scripts/run_cpu.sh accept-toolchain
baseline:
	bash scripts/run_cpu.sh generate --backend opt --out results/opt-v1
	bash scripts/run_cpu.sh evaluate --run results/opt-v1
fixtures:
	bash scripts/run_cpu.sh validate-fixtures
report:
	bash scripts/run_cpu.sh report --runs results/opt-v1 --out reports/generated/baseline
