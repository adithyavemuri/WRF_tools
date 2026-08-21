# Contributing

Issues, documentation improvements, tests, and focused pull requests are
welcome. Please avoid committing WRF output files or other large datasets.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e . --no-deps
python -m pytest
```

New diagnostics should accept NumPy-compatible arrays where practical, state
their axis and unit conventions, and include a numerical test. Public examples
must use relative paths or command-line arguments rather than machine-specific
paths.
